from datetime import date
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from src.nlp.classifier import ClassificationResult, DocumentType
from src.nlp.reconciler import ReconciliationReport, ReconciliationStatus
from src.nlp.schemas import InvoiceExtraction, LineItemExtraction, PaymentVoucherExtraction, ShippingGuideExtraction
from src.services.pipeline_service import (
    DossierProcessingResult,
    PipelineService,
    ProcessedDocument,
    ProcessedPageResult,
)
from src.services.semantic_search import SearchResult, SemanticSearchService
from src.vision.preprocessor import ProcessedPage
from src.vision.spatial_ocr import OCRResult, SpatialToken


def _dummy_token(text: str, ymin: int, xmin: int, ymax: int, xmax: int) -> SpatialToken:
    return SpatialToken(
        text=text,
        confidence=0.9,
        bbox=(ymin, xmin, ymax, xmax),
        raw_box=[[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax]],
    )


def test_pipeline_service_orchestration():
    # Mocking individual engines to verify end-to-end orchestration logic
    mock_preprocessor = MagicMock()
    mock_ocr = MagicMock()
    mock_classifier = MagicMock()
    mock_embeddings = MagicMock()
    mock_extractor = MagicMock()
    mock_reconciler = MagicMock()

    # Preprocessor returns 1 page
    mock_page = ProcessedPage(
        page_number=1,
        image=None,
        original_skew_angle=0.0,
        width=1000,
        height=1400,
    )
    mock_preprocessor.process_file.return_value = [mock_page]

    # OCR returns tokens
    mock_tokens = [
        _dummy_token("DISTRIBUIDORA INDUSTRIAL", 80, 100, 100, 400),
        _dummy_token("RUC: 20549812341", 110, 100, 130, 300),
    ]
    mock_ocr_res = OCRResult(1, mock_tokens, "DISTRIBUIDORA INDUSTRIAL RUC: 20549812341", 1000, 1400)
    mock_ocr.extract_tokens.return_value = mock_ocr_res

    # Classifier classifies as INVOICE
    mock_classifier.classify.return_value = ClassificationResult(
        doc_type=DocumentType.INVOICE,
        confidence=0.95,
        evidence_tokens=["RUC", "FACTURA"],
    )

    # Embeddings returns 384d vector
    mock_embeddings.embed_text.return_value = [0.05] * 384

    # Extractor returns an invoice
    sample_invoice = InvoiceExtraction(
        supplier_ruc="20549812341",
        supplier_name="DISTRIBUIDORA INDUSTRIAL S.A.C.",
        invoice_number="F001-0008492",
        issue_date=date(2026, 10, 28),
        currency="PEN",
        subtotal=100.0,
        tax_amount=18.0,
        total_amount=118.0,
    )
    mock_extractor.extract_invoice.return_value = sample_invoice

    # Reconciler returns report
    mock_reconciler.reconcile.return_value = ReconciliationReport(
        status=ReconciliationStatus.PENDING,
        math_valid=True,
        goods_matched=False,
        payment_matched=False,
        discrepancies=[],
        summary="Expediente pendiente de guias y vouchers",
    )

    service = PipelineService(
        preprocessor=mock_preprocessor,
        ocr_engine=mock_ocr,
        classifier=mock_classifier,
        embedding_engine=mock_embeddings,
        entity_extractor=mock_extractor,
        reconciler=mock_reconciler,
    )

    result = service.process_dossier_files([Path("fake_invoice.pdf")])

    assert isinstance(result, DossierProcessingResult)
    assert len(result.documents) == 1
    assert result.documents[0].doc_type == DocumentType.INVOICE
    assert result.invoice is not None
    assert result.reconciliation_report.status == ReconciliationStatus.PENDING
    assert len(result.documents[0].pages) == 1
    assert len(result.documents[0].pages[0].embedding) == 384


def test_semantic_search_service_query_building():
    mock_embeddings = MagicMock()
    mock_embeddings.embed_text.return_value = [0.1] * 384

    search_service = SemanticSearchService(embedding_engine=mock_embeddings)

    # Mock database session
    mock_db = MagicMock()
    # Mocking the execute and all() response
    mock_row = MagicMock()
    mock_row.page_id = "page-uuid-1"
    mock_row.document_id = "doc-uuid-1"
    mock_row.dossier_id = "dossier-uuid-1"
    mock_row.dossier_title = "Compra Repuestos Octubre"
    mock_row.dossier_status = "RECONCILED"
    mock_row.doc_type = "INVOICE"
    mock_row.similarity_score = 0.89
    mock_row.image_path = "/uploads/page_1.png"

    mock_db.execute.return_value.all.return_value = [mock_row]

    results = search_service.search(
        db=mock_db,
        query="facturas con compra de valvulas",
        limit=5,
        status="RECONCILED",
    )

    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].dossier_title == "Compra Repuestos Octubre"
    assert results[0].similarity_score == 0.89
    mock_embeddings.embed_text.assert_called_once_with("facturas con compra de valvulas")


def test_pipeline_service_save_to_db():
    service = PipelineService()
    mock_db = MagicMock()

    sample_invoice = InvoiceExtraction(
        supplier_ruc="20549812341",
        supplier_name="DISTRIBUIDORA INDUSTRIAL S.A.C.",
        invoice_number="F001-0008492",
        issue_date=date(2026, 10, 28),
        currency="PEN",
        subtotal=100.0,
        tax_amount=18.0,
        total_amount=118.0,
        line_items=[
            LineItemExtraction(
                item_number=1,
                description="VALVULA DE CONTROL",
                quantity=1.0,
                unit_price=100.0,
                line_total=100.0,
            )
        ],
    )

    page_res = ProcessedPageResult(
        page_number=1,
        image_path="/uploads/test_page_1.png",
        ocr_result=OCRResult(1, [], "texto factura", 1000, 1400),
        embedding=[0.01] * 384,
    )

    proc_doc = ProcessedDocument(
        file_path="invoice.pdf",
        doc_type=DocumentType.INVOICE,
        pages=[page_res],
        extraction=sample_invoice,
    )

    reconcile_report = ReconciliationReport(
        status=ReconciliationStatus.RECONCILED,
        math_valid=True,
        goods_matched=True,
        payment_matched=True,
        discrepancies=[],
        summary="Conciliado al 100%",
        total_billed=118.0,
        total_paid=118.0,
        balance_pending=0.0,
    )

    dossier_result = DossierProcessingResult(
        documents=[proc_doc],
        reconciliation_report=reconcile_report,
        invoice=sample_invoice,
    )

    dossier = service.save_to_database(
        db=mock_db,
        title="Expediente de Compra Octubre",
        processing_result=dossier_result,
    )

    assert dossier.title == "Expediente de Compra Octubre"
    assert mock_db.add.called
    assert mock_db.commit.called
    assert mock_db.refresh.called
