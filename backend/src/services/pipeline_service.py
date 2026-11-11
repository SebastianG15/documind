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

            # Consolidar tokens del documento para ubicar coordenadas (bbox) de cada campo
            doc_tokens = [tok for pr in doc.pages for tok in pr.ocr_result.tokens]

            # Guardar extracciones
            if isinstance(doc.extraction, InvoiceExtraction):
                self._save_invoice_extractions(db, db_doc.id, doc.extraction, doc_tokens)
            elif isinstance(doc.extraction, ShippingGuideExtraction):
                self._save_guide_extractions(db, db_doc.id, doc.extraction, doc_tokens)
            elif isinstance(doc.extraction, PaymentVoucherExtraction):
                self._save_voucher_extractions(db, db_doc.id, doc.extraction, doc_tokens)

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

    def _merge_row_bbox(self, anchor, tokens) -> dict:
        row_toks = [t for t in tokens if abs(t.bbox[0] - anchor.bbox[0]) <= 16]
        return {
            "ymin": int(min(t.bbox[0] for t in row_toks)),
            "xmin": int(min(t.bbox[1] for t in row_toks)),
            "ymax": int(max(t.bbox[2] for t in row_toks)),
            "xmax": int(max(t.bbox[3] for t in row_toks)),
        }

    def _resolve_field_bbox(self, field_name: str, field_value: str, tokens) -> Optional[dict]:
        if not tokens or not field_value:
            return None

        val_upper = str(field_value).strip().upper()

        if field_name in ("SUPPLIER_RUC", "SENDER_RUC", "RECIPIENT_RUC"):
            for tok in tokens:
                t_up = tok.text.upper()
                if val_upper in t_up or "RUC" in t_up:
                    ymin, xmin, ymax, xmax = tok.bbox
                    if "REMITENTE" in t_up and "DESTINATARIO" in t_up:
                        mid = xmin + int((xmax - xmin) * 0.49)
                        if field_name == "SENDER_RUC":
                            return {"ymin": int(ymin), "xmin": int(xmin), "ymax": int(ymax), "xmax": mid}
                        if field_name == "RECIPIENT_RUC":
                            return {"ymin": int(ymin), "xmin": mid + 8, "ymax": int(ymax), "xmax": int(xmax)}
                    if " - " in t_up and val_upper in t_up.split(" - ")[0]:
                        return {
                            "ymin": int(ymin),
                            "xmin": int(xmin),
                            "ymax": int(ymax),
                            "xmax": xmin + int((xmax - xmin) * 0.44),
                        }
                    if val_upper in t_up:
                        return {"ymin": int(ymin), "xmin": int(xmin), "ymax": int(ymax), "xmax": int(xmax)}

        if field_name in ("SUPPLIER_NAME", "BANK_NAME"):
            keywords = [w for w in val_upper.split() if len(w) >= 3][:2]
            for tok in sorted(tokens, key=lambda t: t.bbox[0]):
                t_up = tok.text.upper()
                if tok.bbox[0] < 220 and any(k in t_up for k in keywords):
                    return self._merge_row_bbox(tok, tokens)

        if field_name in ("INVOICE_NUMBER", "GUIDE_NUMBER", "OPERATION_NUMBER"):
            label_keys = {
                "INVOICE_NUMBER": ["FACTURA", val_upper],
                "GUIDE_NUMBER": ["GUIA DE REMISION", val_upper],
                "OPERATION_NUMBER": ["NUMERO DE OPERACION", "NRO. OP", val_upper],
            }[field_name]
            for tok in tokens:
                t_up = tok.text.upper()
                if val_upper in t_up or any(k in t_up for k in label_keys):
                    return self._merge_row_bbox(tok, tokens)

        if field_name in ("ISSUE_DATE", "PAYMENT_DATE"):
            for tok in tokens:
                t_up = tok.text.upper()
                if "FECHA" in t_up or val_upper in t_up:
                    ymin, xmin, ymax, xmax = tok.bbox
                    if "MONEDA" in t_up:
                        return {
                            "ymin": int(ymin),
                            "xmin": int(xmin),
                            "ymax": int(ymax),
                            "xmax": xmin + int((xmax - xmin) * 0.50),
                        }
                    row_has_moneda = any(
                        "MONEDA" in t.text.upper() for t in tokens if abs(t.bbox[0] - ymin) <= 16 and t is not tok
                    )
                    if row_has_moneda:
                        return {"ymin": int(ymin), "xmin": int(xmin), "ymax": int(ymax), "xmax": int(xmax)}
                    return self._merge_row_bbox(tok, tokens)

        if field_name == "CURRENCY":
            for tok in tokens:
                t_up = tok.text.upper()
                if "MONEDA" in t_up or "SOLES" in t_up or "DOLARES" in t_up or val_upper in t_up:
                    ymin, xmin, ymax, xmax = tok.bbox
                    if "FECHA" in t_up and "MONEDA" in t_up:
                        return {
                            "ymin": int(ymin),
                            "xmin": xmin + int((xmax - xmin) * 0.51),
                            "ymax": int(ymax),
                            "xmax": int(xmax),
                        }
                    row_has_fecha = any(
                        "FECHA" in t.text.upper() for t in tokens if abs(t.bbox[0] - ymin) <= 16 and t is not tok
                    )
                    if row_has_fecha:
                        return {"ymin": int(ymin), "xmin": int(xmin), "ymax": int(ymax), "xmax": int(xmax)}
                    return self._merge_row_bbox(tok, tokens)

        if field_name == "SUBTOTAL":
            for tok in tokens:
                t_up = tok.text.upper()
                if any(k in t_up for k in ["SUBTOTAL", "OP. GRAVADA", "VALOR VENTA"]):
                    return self._merge_row_bbox(tok, tokens)

        if field_name == "TAX_AMOUNT":
            for tok in tokens:
                t_up = tok.text.upper()
                if any(k in t_up for k in ["IGV", "I.G.V", "18%", "IMPUESTO"]):
                    return self._merge_row_bbox(tok, tokens)

        if field_name in ("TOTAL_AMOUNT", "AMOUNT"):
            for tok in tokens:
                t_up = tok.text.upper()
                if "SUBTOTAL" in t_up or tok.bbox[0] < 280:
                    continue
                if any(k in t_up for k in ["TOTAL FACTURA", "TOTAL A PAGAR", "IMPORTE TOTAL", "TRANSFERIDO", "MONTO", "TOTAL:"]):
                    return self._merge_row_bbox(tok, tokens)

        if field_name in ("ORIGIN_ADDRESS", "DESTINATION_ADDRESS", "SOURCE_ACCOUNT", "DESTINATION_ACCOUNT"):
            label_map = {
                "ORIGIN_ADDRESS": ["PUNTO DE PARTIDA", "ORIGEN"],
                "DESTINATION_ADDRESS": ["PUNTO DE LLEGADA", "DESTINO"],
                "SOURCE_ACCOUNT": ["CUENTA ORIGEN", "ORIGEN", "DEBITO"],
                "DESTINATION_ACCOUNT": ["CUENTA DESTINO", "BENEFICIARIO", "DESTINO", "CREDITO"],
            }[field_name]
            for tok in tokens:
                t_up = tok.text.upper()
                if any(k in t_up for k in label_map) or (len(val_upper) >= 5 and val_upper[:10] in t_up):
                    return self._merge_row_bbox(tok, tokens)

        # Fallback: direct substring match
        for tok in tokens:
            if val_upper in tok.text.upper():
                ymin, xmin, ymax, xmax = tok.bbox
                return {"ymin": int(ymin), "xmin": int(xmin), "ymax": int(ymax), "xmax": int(xmax)}

        return None

    def _save_invoice_extractions(
        self, db: Session, doc_id: uuid.UUID, inv: InvoiceExtraction, tokens=None
    ) -> None:
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
            bbox_dict = self._resolve_field_bbox(name, val, tokens or [])
            db.add(
                DBExtraction(
                    document_id=doc_id,
                    field_name=name,
                    field_value=val,
                    confidence=1.0,
                    bbox_ymin=bbox_dict["ymin"] if bbox_dict else None,
                    bbox_xmin=bbox_dict["xmin"] if bbox_dict else None,
                    bbox_ymax=bbox_dict["ymax"] if bbox_dict else None,
                    bbox_xmax=bbox_dict["xmax"] if bbox_dict else None,
                )
            )

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

    def _save_guide_extractions(
        self, db: Session, doc_id: uuid.UUID, guide: ShippingGuideExtraction, tokens=None
    ) -> None:
        fields = [
            ("GUIDE_NUMBER", guide.guide_number),
            ("SENDER_RUC", guide.sender_ruc),
            ("RECIPIENT_RUC", guide.recipient_ruc),
            ("ISSUE_DATE", str(guide.issue_date)),
            ("ORIGIN_ADDRESS", guide.origin_address or ""),
            ("DESTINATION_ADDRESS", guide.destination_address or ""),
        ]
        for name, val in fields:
            bbox_dict = self._resolve_field_bbox(name, val, tokens or [])
            db.add(
                DBExtraction(
                    document_id=doc_id,
                    field_name=name,
                    field_value=val,
                    confidence=1.0,
                    bbox_ymin=bbox_dict["ymin"] if bbox_dict else None,
                    bbox_xmin=bbox_dict["xmin"] if bbox_dict else None,
                    bbox_ymax=bbox_dict["ymax"] if bbox_dict else None,
                    bbox_xmax=bbox_dict["xmax"] if bbox_dict else None,
                )
            )

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

    def _save_voucher_extractions(
        self, db: Session, doc_id: uuid.UUID, voucher: PaymentVoucherExtraction, tokens=None
    ) -> None:
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
            bbox_dict = self._resolve_field_bbox(name, val, tokens or [])
            db.add(
                DBExtraction(
                    document_id=doc_id,
                    field_name=name,
                    field_value=val,
                    confidence=1.0,
                    bbox_ymin=bbox_dict["ymin"] if bbox_dict else None,
                    bbox_xmin=bbox_dict["xmin"] if bbox_dict else None,
                    bbox_ymax=bbox_dict["ymax"] if bbox_dict else None,
                    bbox_xmax=bbox_dict["xmax"] if bbox_dict else None,
                )
            )
