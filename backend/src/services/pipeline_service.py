from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union
import uuid

import cv2
import numpy as np
from sqlalchemy.orm import Session

from src.db.models import (
    Document as DBDocument,
    DocumentPage as DBDocumentPage,
    DocumentType as DBDocumentType,
    Dossier as DBDossier,
    DossierStatus as DBDossierStatus,
    Extraction as DBExtraction,
    LineItem as DBLineItem,
    ReconciliationResult as DBReconciliationResult,
)
from src.nlp.classifier import DocumentClassifier, DocumentType
from src.nlp.embeddings import EmbeddingEngine
from src.nlp.entity_extractor import EntityExtractor
from src.nlp.reconciler import ReconciliationReport, ReconciliationStatus, ThreeWayReconciler
from src.nlp.schemas import (
    InvoiceExtraction,
    PaymentVoucherExtraction,
    ShippingGuideExtraction,
)
from src.vision.preprocessor import DocumentPreprocessor, ProcessedPage
from src.vision.spatial_ocr import OCRResult, SpatialOCREngine


@dataclass
class ProcessedPageResult:
    page_number: int
    image_path: str
    ocr_result: OCRResult
    embedding: List[float]


@dataclass
class ProcessedDocument:
    file_path: str
    doc_type: DocumentType
    pages: List[ProcessedPageResult]
    extraction: Optional[Union[InvoiceExtraction, ShippingGuideExtraction, PaymentVoucherExtraction]] = None


@dataclass
class DossierProcessingResult:
    documents: List[ProcessedDocument]
    reconciliation_report: ReconciliationReport
    invoice: Optional[InvoiceExtraction] = None
    shipping_guides: List[ShippingGuideExtraction] = field(default_factory=list)
    payment_vouchers: List[PaymentVoucherExtraction] = field(default_factory=list)


class PipelineService:
    """Servicio orquestador del pipeline completo de inteligencia documental contable."""

    def __init__(
        self,
        preprocessor: Optional[DocumentPreprocessor] = None,
        ocr_engine: Optional[SpatialOCREngine] = None,
        classifier: Optional[DocumentClassifier] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
        entity_extractor: Optional[EntityExtractor] = None,
        reconciler: Optional[ThreeWayReconciler] = None,
        upload_dir: Union[str, Path] = "uploads",
    ) -> None:
        self.preprocessor = preprocessor or DocumentPreprocessor()
        self.ocr_engine = ocr_engine or SpatialOCREngine()
        self.classifier = classifier or DocumentClassifier()
        self.embedding_engine = embedding_engine or EmbeddingEngine()
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.reconciler = reconciler or ThreeWayReconciler()
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def process_dossier_files(self, file_paths: List[Union[str, Path]]) -> DossierProcessingResult:
        processed_docs: List[ProcessedDocument] = []
        invoice: Optional[InvoiceExtraction] = None
        shipping_guides: List[ShippingGuideExtraction] = []
        payment_vouchers: List[PaymentVoucherExtraction] = []

        for fpath in file_paths:
            path_obj = Path(fpath)
            doc_pages = self.preprocessor.process_file(path_obj)
            pages_results: List[ProcessedPageResult] = []
            doc_full_text = []

            for page in doc_pages:
                ocr_result = self.ocr_engine.extract_tokens(page.image, page_number=page.page_number)
                doc_full_text.append(ocr_result.full_text)

                # Persistir imagen corregida si existe en memoria
                img_name = f"page_{uuid.uuid4().hex[:8]}_{page.page_number}.png"
                img_path = self.upload_dir / img_name
                if page.image is not None:
                    cv2.imwrite(str(img_path), page.image)

                vector = self.embedding_engine.embed_text(ocr_result.full_text)
                pages_results.append(
                    ProcessedPageResult(
                        page_number=page.page_number,
                        image_path=str(img_path),
                        ocr_result=ocr_result,
                        embedding=vector,
                    )
                )

            combined_text = " ".join(doc_full_text)
            classification = self.classifier.classify(combined_text)

            # Consolidar tokens para extraccion de entidades
            all_tokens = [tok for pr in pages_results for tok in pr.ocr_result.tokens]
            agg_ocr = OCRResult(
                page_number=1,
                tokens=all_tokens,
                full_text=combined_text,
                width=pages_results[0].ocr_result.width if pages_results else 1000,
                height=pages_results[0].ocr_result.height if pages_results else 1000,
            )

            extraction = None
            if classification.doc_type == DocumentType.INVOICE:
                extraction = self.entity_extractor.extract_invoice(agg_ocr)
                invoice = extraction
            elif classification.doc_type == DocumentType.SHIPPING_GUIDE:
                extraction = self.entity_extractor.extract_shipping_guide(agg_ocr)
                shipping_guides.append(extraction)
            elif classification.doc_type == DocumentType.PAYMENT_VOUCHER:
                extraction = self.entity_extractor.extract_payment_voucher(agg_ocr)
                payment_vouchers.append(extraction)

            processed_docs.append(
                ProcessedDocument(
                    file_path=str(path_obj),
                    doc_type=classification.doc_type,
                    pages=pages_results,
                    extraction=extraction,
                )
            )

        # 3-Way Reconciliation
        if invoice is not None:
            reconcile_report = self.reconciler.reconcile(
                invoice=invoice,
                shipping_guides=shipping_guides,
                payment_vouchers=payment_vouchers,
            )
        else:
            reconcile_report = ReconciliationReport(
                status=ReconciliationStatus.PENDING,
                math_valid=False,
                goods_matched=False,
                payment_matched=False,
                discrepancies=[{"type": "MISSING_INVOICE", "detail": "No se detecto factura comercial en el expediente"}],
                summary="Expediente sin factura principal para cotejo de 3 vias.",
            )

        return DossierProcessingResult(
            documents=processed_docs,
            reconciliation_report=reconcile_report,
            invoice=invoice,
            shipping_guides=shipping_guides,
            payment_vouchers=payment_vouchers,
        )

    def save_to_database(
        self,
        db: Session,
        title: str,
        processing_result: DossierProcessingResult,
    ) -> DBDossier:
        # Mapear estado
        status_map = {
            ReconciliationStatus.RECONCILED: DBDossierStatus.RECONCILED,
            ReconciliationStatus.DISCREPANCY_FOUND: DBDossierStatus.DISCREPANCY_FOUND,
            ReconciliationStatus.PENDING: DBDossierStatus.PENDING,
        }
        dossier_status = status_map.get(processing_result.reconciliation_report.status, DBDossierStatus.PENDING)

        dossier = DBDossier(title=title, status=dossier_status)
        db.add(dossier)
        db.flush()

        # Guardar documentos y paginas
        for doc in processing_result.documents:
            db_doc = DBDocument(
                dossier_id=dossier.id,
                doc_type=DBDocumentType(doc.doc_type.value),
                file_path=doc.file_path,
            )
            db.add(db_doc)
            db.flush()

            for page in doc.pages:
                db_page = DBDocumentPage(
                    document_id=db_doc.id,
                    page_number=page.page_number,
                    image_path=page.image_path,
                    embedding=page.embedding,
                )
                db.add(db_page)

            # Guardar extracciones
            if isinstance(doc.extraction, InvoiceExtraction):
                self._save_invoice_extractions(db, db_doc.id, doc.extraction)
            elif isinstance(doc.extraction, ShippingGuideExtraction):
                self._save_guide_extractions(db, db_doc.id, doc.extraction)
            elif isinstance(doc.extraction, PaymentVoucherExtraction):
                self._save_voucher_extractions(db, db_doc.id, doc.extraction)

        # Guardar resultado de reconciliacion
        rep = processing_result.reconciliation_report
        db_reconcile = DBReconciliationResult(
            dossier_id=dossier.id,
            math_valid=rep.math_valid,
            goods_matched=rep.goods_matched,
            payment_matched=rep.payment_matched,
            discrepancy_details={"summary": rep.summary, "discrepancies": rep.discrepancies},
        )
        db.add(db_reconcile)
        db.commit()
        db.refresh(dossier)

        return dossier

    def _save_invoice_extractions(self, db: Session, doc_id: uuid.UUID, inv: InvoiceExtraction) -> None:
        fields = [
            ("SUPPLIER_RUC", inv.supplier_ruc),
            ("SUPPLIER_NAME", inv.supplier_name),
            ("INVOICE_NUMBER", inv.invoice_number),
            ("ISSUE_DATE", str(inv.issue_date)),
            ("CURRENCY", inv.currency),
            ("SUBTOTAL", str(inv.subtotal)),
            ("TAX_AMOUNT", str(inv.tax_amount)),
            ("TOTAL_AMOUNT", str(inv.total_amount)),
        ]
        for name, val in fields:
            db.add(DBExtraction(document_id=doc_id, field_name=name, field_value=val, confidence=1.0))

        for item in inv.line_items:
            bbox_dict = item.bbox.model_dump() if item.bbox else None
            db.add(
                DBLineItem(
                    document_id=doc_id,
                    sku=item.sku,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                    bbox=bbox_dict,
                )
            )

    def _save_guide_extractions(self, db: Session, doc_id: uuid.UUID, guide: ShippingGuideExtraction) -> None:
        fields = [
            ("GUIDE_NUMBER", guide.guide_number),
            ("SENDER_RUC", guide.sender_ruc),
            ("RECIPIENT_RUC", guide.recipient_ruc),
            ("ISSUE_DATE", str(guide.issue_date)),
            ("ORIGIN_ADDRESS", guide.origin_address or ""),
            ("DESTINATION_ADDRESS", guide.destination_address or ""),
        ]
        for name, val in fields:
            db.add(DBExtraction(document_id=doc_id, field_name=name, field_value=val, confidence=1.0))

        for item in guide.items:
            bbox_dict = item.bbox.model_dump() if item.bbox else None
            db.add(
                DBLineItem(
                    document_id=doc_id,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=0.0,
                    line_total=0.0,
                    bbox=bbox_dict,
                )
            )

    def _save_voucher_extractions(self, db: Session, doc_id: uuid.UUID, voucher: PaymentVoucherExtraction) -> None:
        fields = [
            ("BANK_NAME", voucher.bank_name),
            ("OPERATION_NUMBER", voucher.operation_number),
            ("AMOUNT", str(voucher.amount)),
            ("CURRENCY", voucher.currency),
            ("PAYMENT_DATE", str(voucher.payment_date)),
            ("SOURCE_ACCOUNT", voucher.source_account or ""),
            ("DESTINATION_ACCOUNT", voucher.destination_account or ""),
        ]
        for name, val in fields:
            db.add(DBExtraction(document_id=doc_id, field_name=name, field_value=val, confidence=1.0))
