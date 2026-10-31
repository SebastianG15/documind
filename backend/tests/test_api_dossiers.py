import io
from unittest.mock import MagicMock, patch
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from src.db.base import get_db
from src.main import app
from src.nlp.reconciler import ReconciliationReport, ReconciliationStatus
from src.services.pipeline_service import DossierProcessingResult, ProcessedDocument
from src.services.semantic_search import SearchResult

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "DocuMind" in data["service"]


def test_upload_dossier_missing_fields():
    # Envio sin archivos debe fallar con 422 Unprocessable Entity
    response = client.post("/api/v1/dossiers/upload", data={"title": "Test Dossier"})
    assert response.status_code == 422


@patch("src.api.v1.dossiers.pipeline_service")
def test_upload_dossier_successful(mock_pipeline):
    fake_dossier_id = uuid4()
    mock_dossier = MagicMock()
    mock_dossier.id = fake_dossier_id
    mock_dossier.title = "Compra de Maquinaria"
    mock_dossier.status.value = "RECONCILED"

    mock_rep = ReconciliationReport(
        status=ReconciliationStatus.RECONCILED,
        math_valid=True,
        goods_matched=True,
        payment_matched=True,
        discrepancies=[],
        summary="Cotejo 100% conciliado",
        total_billed=1000.0,
        total_paid=1000.0,
        balance_pending=0.0,
    )

    mock_res = DossierProcessingResult(
        documents=[MagicMock()],
        reconciliation_report=mock_rep,
    )

    mock_pipeline.process_dossier_files.return_value = mock_res
    mock_pipeline.save_to_database.return_value = mock_dossier

    # Mock DB dependency
    app.dependency_overrides[get_db] = lambda: MagicMock()

    try:
        files = [
            ("files", ("factura.pdf", io.BytesIO(b"%PDF-1.4 fake invoice content"), "application/pdf")),
        ]
        response = client.post(
            "/api/v1/dossiers/upload",
            data={"title": "Compra de Maquinaria"},
            files=files,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["dossier_id"] == str(fake_dossier_id)
        assert data["title"] == "Compra de Maquinaria"
        assert data["status"] == "RECONCILED"
        assert data["math_valid"] is True
        assert data["goods_matched"] is True
        assert data["payment_matched"] is True
    finally:
        app.dependency_overrides.clear()


def test_get_dossier_not_found():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        random_id = uuid4()
        response = client.get(f"/api/v1/dossiers/{random_id}")
        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@patch("src.api.v1.dossiers.search_service")
def test_search_dossiers_endpoint(mock_search):
    mock_search.search.return_value = [
        SearchResult(
            page_id=str(uuid4()),
            document_id=str(uuid4()),
            dossier_id=str(uuid4()),
            dossier_title="Compra de Sensores",
            dossier_status="RECONCILED",
            doc_type="INVOICE",
            similarity_score=0.92,
            image_path="/uploads/page_1.png",
        )
    ]

    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        payload = {
            "query": "sensores de temperatura",
            "limit": 5,
            "status": "RECONCILED",
        }
        response = client.post("/api/v1/dossiers/search", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 1
        assert data["results"][0]["dossier_title"] == "Compra de Sensores"
        assert data["results"][0]["similarity_score"] == 0.92
    finally:
        app.dependency_overrides.clear()
