"""Modulo de seguridad, saneamiento de archivos y cabeceras de proteccion HTTP.

Implementa:
- Validacion estricta de Magic Bytes binarios (PDF, JPEG, PNG).
- Saneamiento y mitigacion contra Path Traversal y extension spoofing.
- Limites de cuota por archivo y por lote (prevencion de DoS por memoria/disco).
- Middleware de cabeceras HTTP de seguridad (OWASP Top 10).
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Tuple
from uuid import uuid4

from fastapi import HTTPException, Request, UploadFile, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.core.config import settings

# Magic Bytes binarios estandar para documentos validos
MAGIC_NUMBERS = {
    "application/pdf": b"%PDF-",
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
}

# Extensiones de archivo autorizadas
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inyecta cabeceras HTTP de seguridad estandar en todas las respuestas."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline';"
        )
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


def sanitize_filename(filename: str) -> str:
    """Sanea nombres de archivo eliminando rutas relativas, path traversal y caracteres peligrosos."""
    if not filename:
        return f"doc_{uuid4().hex[:8]}.pdf"

    # Remover bytes nulos potenciales
    cleaned = filename.replace("\x00", "")

    # Remover rutas absolutas y relativas tanto POSIX como Windows
    cleaned = cleaned.replace("\\", "/").split("/")[-1]
    cleaned = Path(cleaned).name

    # Normalizar Unicode a ASCII plano
    nfkd = unicodedata.normalize("NFKD", cleaned)
    ascii_name = nfkd.encode("ASCII", "ignore").decode("utf-8")

    p = Path(ascii_name)
    ext = p.suffix.lower()
    stem = p.stem

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extension '{ext}' no permitida. Solo se admiten: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Sustituir caracteres especiales por guiones bajos
    safe_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", stem).strip("._")
    if not safe_stem:
        safe_stem = f"file_{uuid4().hex[:8]}"

    # Acotar longitud del nombre
    safe_stem = safe_stem[:64]

    return f"{uuid4().hex[:8]}_{safe_stem}{ext}"


def validate_magic_bytes(header: bytes, expected_ext: str) -> str:
    """Valida los primeros bytes del archivo contra firmas binarias conocidas."""
    if expected_ext == ".pdf":
        if header.startswith(MAGIC_NUMBERS["application/pdf"]):
            return "application/pdf"
    elif expected_ext in {".jpg", ".jpeg"}:
        if header.startswith(MAGIC_NUMBERS["image/jpeg"]):
            return "image/jpeg"
    elif expected_ext == ".png":
        if header.startswith(MAGIC_NUMBERS["image/png"]):
            return "image/png"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Firma binaria (Magic Bytes) invalida para la extension '{expected_ext}'. Archivo posiblemente corrupto o camuflado.",
    )


async def validate_and_save_upload_file(
    file: UploadFile,
    target_dir: Path,
    max_file_size: int = settings.MAX_FILE_SIZE_BYTES,
) -> Tuple[Path, int]:
    """Valida cuota, extension, magic bytes y almacena el archivo en disco de forma segura."""
    original_name = file.filename or "unknown.pdf"
    safe_name = sanitize_filename(original_name)
    ext = Path(safe_name).suffix.lower()

    dest_path = (target_dir / safe_name).resolve()
    target_dir_resolved = target_dir.resolve()

    # Validacion estricta contra path traversal
    if not str(dest_path).startswith(str(target_dir_resolved)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Intento de Path Traversal detectado en el nombre de archivo.",
        )

    chunk_size = 64 * 1024  # 64 KB
    total_bytes = 0
    first_chunk = True

    try:
        with dest_path.open("wb") as out_file:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break

                total_bytes += len(chunk)
                if total_bytes > max_file_size:
                    out_file.close()
                    dest_path.unlink(missing_ok=True)
                    max_mb = max_file_size // (1024 * 1024)
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE if hasattr(status, "HTTP_413_CONTENT_TOO_LARGE") else 413,
                        detail=f"El archivo '{original_name}' excede el tamano maximo permitido de {max_mb} MB.",
                    )

                if first_chunk:
                    validate_magic_bytes(chunk[:32], ext)
                    first_chunk = False

                out_file.write(chunk)
    except Exception:
        # En caso de excepcion (HTTPException u otro error), limpiar archivo incompleto
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        raise

    if total_bytes == 0:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo '{original_name}' esta vacio (0 bytes).",
        )

    return dest_path, total_bytes
