"""Suite de pruebas de integracion End-to-End, seguridad y resiliencia.

Valida:
1. Inyeccion de cabeceras HTTP de seguridad (OWASP).
2. Rechazo de extensiones ejecutables o no permitidas.
3. Deteccion y bloqueo de extension spoofing mediante Magic Bytes binarios.
4. Mitigacion de ataques de Path Traversal en nombres de archivo.
5. Control de cuotas por archivo y rechazo de payloads sobredimensionados (HTTP 413).
6. Limite de cantidad de comprobantes por expediente.
7. Degradacion elegante (HTTP 422) ante documentos corruptos o no procesables.
"""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.core.config import settings
from src.core.security import sanitize_filename, validate_magic_bytes
from src.db.base import get_db
from src.main import app
from src.nlp.reconciler import ReconciliationReport, ReconciliationStatus
from src.services.pipeline_service import DossierProcessingResult

client = TestClient(app)


def test_security_headers_injected_on_responses():
    """Verifica que el middleware inyecte cabeceras de proteccion en las respuestas HTTP."""
    response = client.get("/health")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
    assert "camera=()" in headers.get("Permissions-Policy", "")


def test_upload_rejected_for_disallowed_extension():
    """Verifica el rechazo inmediato de extensiones ejecutables o de script."""
    malicious_files = [
        ("files", ("exploit.exe", io.BytesIO(b"binary executable payload"), "application/octet-stream")),
    ]
    response = client.post(
        "/api/v1/dossiers/upload",
        data={"title": "Intento de Ataque"},
        files=malicious_files,
    )
    assert response.status_code == 400
    assert "Extension '.exe' no permitida" in response.json()["detail"]


def test_upload_rejected_for_spoofed_pdf_magic_bytes():
    """Verifica que un archivo .pdf con contenido ejecutable (spoofed) sea bloqueado."""
    # Archivo con extension .pdf pero cabecera binaria MZ (PE Windows Executable)
    pe_header = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    files = [
        ("files", ("trojan.pdf", io.BytesIO(pe_header), "application/pdf")),
    ]
    response = client.post(
        "/api/v1/dossiers/upload",
        data={"title": "Factura Camuflada"},
        files=files,
    )
    assert response.status_code == 400
    assert "Magic Bytes" in response.json()["detail"]


def test_upload_rejected_for_spoofed_jpeg_magic_bytes():
    """Verifica que un archivo .jpg que contenga un script de bash sea bloqueado."""
    shell_script = b"#!/bin/bash\nrm -rf /tmp/data\n"
    files = [
        ("files", ("voucher.jpg", io.BytesIO(shell_script), "image/jpeg")),
    ]
    response = client.post(
        "/api/v1/dossiers/upload",
        data={"title": "Voucher Falsificado"},
        files=files,
    )
    assert response.status_code == 400
    assert "Magic Bytes" in response.json()["detail"]


def test_upload_rejected_for_empty_file():
    """Verifica el rechazo de archivos vacios (0 bytes)."""
    files = [
        ("files", ("factura_vacia.pdf", io.BytesIO(b""), "application/pdf")),
    ]
    response = client.post(
        "/api/v1/dossiers/upload",
        data={"title": "Expediente Incompleto"},
        files=files,
    )
    assert response.status_code == 400
    assert "esta vacio" in response.json()["detail"]


def test_upload_rejected_for_too_many_files():
    """Verifica que no se permita exceder el maximo de comprobantes por expediente (max 10)."""
    files = [
        (
            "files",
            (
                f"doc_{i}.pdf",
                io.BytesIO(b"%PDF-1.4 fake valid header content"),
                "application/pdf",
            ),
        )
        for i in range(11)
    ]
    response = client.post(
        "/api/v1/dossiers/upload",
        data={"title": "Lote Excesivo"},
        files=files,
    )
    assert response.status_code == 400
    assert "limite maximo de 10 archivos" in response.json()["detail"]


def test_upload_rejected_for_oversized_file(monkeypatch):
    """Verifica el retorno de HTTP 413 ante archivos que superan la cuota maxima de tamano."""
    # Simular cuota pequena de 128 bytes para la prueba
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_BYTES", 128)

    oversized_content = b"%PDF-1.4 " + (b"A" * 500)
    files = [
        ("files", ("factura_gigante.pdf", io.BytesIO(oversized_content), "application/pdf")),
    ]
    response = client.post(
        "/api/v1/dossiers/upload",
        data={"title": "Archivo Sobredimensionado"},
        files=files,
    )
    assert response.status_code == 413
    assert "excede el tamano maximo" in response.json()["detail"]


def test_path_traversal_sanitization():
    """Verifica que rutas con ../ o ..\\ sean limpiadas a un nombre seguro sin escapar."""
    unsafe_name_posix = "../../../../etc/passwd.pdf"
    safe_posix = sanitize_filename(unsafe_name_posix)
    assert ".." not in safe_posix
    assert "/" not in safe_posix
    assert safe_posix.endswith(".pdf")
    assert "passwd" in safe_posix

    unsafe_name_win = "..\\..\\windows\\system32\\cmd.exe.pdf"
    safe_win = sanitize_filename(unsafe_name_win)
    assert ".." not in safe_win
    assert "\\" not in safe_win
    assert safe_win.endswith(".pdf")


@patch("src.api.v1.dossiers.pipeline_service")
def test_corrupt_pdf_graceful_degradation(mock_pipeline):
    """Verifica que una falla de rasterizado/procesamiento devuelva HTTP 422 sin tumbar el worker."""
    mock_pipeline.process_dossier_files.side_effect = ValueError("El archivo PDF esta truncado o corrupto internamente.")

    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        files = [
            ("files", ("danado.pdf", io.BytesIO(b"%PDF-1.4 header but damaged body"), "application/pdf")),
        ]
        response = client.post(
            "/api/v1/dossiers/upload",
            data={"title": "PDF Corrupto"},
            files=files,
        )
        assert response.status_code == 422
        assert "Fallo en el procesamiento" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@patch("src.api.v1.dossiers.pipeline_service")
def test_valid_multiformat_upload_png_and_jpeg(mock_pipeline):
    """Verifica que comprobantes en formatos PNG y JPEG validos sean admitidos exitosamente."""
    fake_dossier_id = uuid4()
    mock_dossier = MagicMock()
    mock_dossier.id = fake_dossier_id
    mock_dossier.title = "Voucher y Guia Escaneados"
    mock_dossier.status.value = "RECONCILED"

    mock_rep = ReconciliationReport(
        status=ReconciliationStatus.RECONCILED,
        math_valid=True,
        goods_matched=True,
        payment_matched=True,
        discrepancies=[],
        summary="Conciliacion exitosa",
        total_billed=500.0,
        total_paid=500.0,
        balance_pending=0.0,
    )
    mock_pipeline.process_dossier_files.return_value = DossierProcessingResult(
        documents=[MagicMock(), MagicMock()],
        reconciliation_report=mock_rep,
    )
    mock_pipeline.save_to_database.return_value = mock_dossier

    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        valid_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + (b"\x00" * 20)
        valid_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF" + (b"\x00" * 20)

        files = [
            ("files", ("guia_almacen.png", io.BytesIO(valid_png), "image/png")),
            ("files", ("voucher_banco.jpg", io.BytesIO(valid_jpeg), "image/jpeg")),
        ]
        response = client.post(
            "/api/v1/dossiers/upload",
            data={"title": "Voucher y Guia Escaneados"},
            files=files,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["dossier_id"] == str(fake_dossier_id)
        assert data["status"] == "RECONCILED"
        assert data["documents_processed"] == 2
    finally:
        app.dependency_overrides.clear()
