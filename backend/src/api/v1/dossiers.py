from pathlib import Path
import shutil
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.security import validate_and_save_upload_file
from src.db.base import get_db
from src.db.models import (
    Document as DBDocument,
    DocumentPage as DBDocumentPage,
    Dossier as DBDossier,
    ReconciliationResult as DBReconciliationResult,
)
from src.schemas.api_schemas import (
    DocumentDetail,
    DossierDetailResponse,
    DossierUploadResponse,
    ExtractionItem,
    LineItemDetail,
    ReconciliationDetail,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from src.services.pipeline_service import PipelineService
from src.services.semantic_search import SemanticSearchService

router = APIRouter(prefix="/dossiers", tags=["Dossiers"])

pipeline_service = PipelineService(upload_dir=settings.UPLOAD_DIR)
search_service = SemanticSearchService()


@router.post("/upload", response_model=DossierUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_dossier(
    title: str = Form(..., min_length=2, max_length=255),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Sube multiples comprobantes (Factura, Guias, Vouchers) y ejecuta el pipeline de conciliacion de 3 vias."""
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debe adjuntar al menos un archivo")

    if len(files) > settings.MAX_FILES_PER_DOSSIER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Se excedio el limite maximo de {settings.MAX_FILES_PER_DOSSIER} archivos por expediente.",
        )

    temp_folder = settings.UPLOAD_DIR / f"temp_{uuid4().hex}"
    temp_folder.mkdir(parents=True, exist_ok=True)
    saved_file_paths: List[Path] = []

    try:
        total_dossier_bytes = 0
        for file in files:
            dest_path, file_bytes = await validate_and_save_upload_file(
                file=file,
                target_dir=temp_folder,
                max_file_size=settings.MAX_FILE_SIZE_BYTES,
            )
            total_dossier_bytes += file_bytes
            if total_dossier_bytes > settings.MAX_DOSSIER_SIZE_BYTES:
                max_total_mb = settings.MAX_DOSSIER_SIZE_BYTES // (1024 * 1024)
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE if hasattr(status, "HTTP_413_CONTENT_TOO_LARGE") else 413,
                    detail=f"El tamano total del expediente excede el limite de {max_total_mb} MB.",
                )
            saved_file_paths.append(dest_path)

        # Ejecutar pipeline completo con manejo elegante de excepciones
        try:
            processing_result = pipeline_service.process_dossier_files(saved_file_paths)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
                detail=f"Fallo en el procesamiento de comprobantes: {str(exc)}",
            )

        # Persistir en base de datos PostgreSQL + pgvector
        saved_dossier = pipeline_service.save_to_database(db, title, processing_result)

        rep = processing_result.reconciliation_report
        return DossierUploadResponse(
            dossier_id=saved_dossier.id,
            title=saved_dossier.title,
            status=saved_dossier.status.value,
            documents_processed=len(processing_result.documents),
            reconciliation_summary=rep.summary,
            math_valid=rep.math_valid,
            goods_matched=rep.goods_matched,
            payment_matched=rep.payment_matched,
        )
    finally:
        # Limpieza de archivos temporales de entrada
        shutil.rmtree(temp_folder, ignore_errors=True)


@router.get("/{dossier_id}", response_model=DossierDetailResponse)
def get_dossier_detail(dossier_id: UUID, db: Session = Depends(get_db)):
    """Obtiene el detalle completo de un expediente contable con sus documentos, items y resultado de cotejo."""
    dossier = db.query(DBDossier).filter(DBDossier.id == dossier_id).first()
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Expediente {dossier_id} no encontrado")

    docs_detail: List[DocumentDetail] = []
    for doc in dossier.documents:
        extractions = [
            ExtractionItem(
                field_name=e.field_name,
                field_value=e.field_value,
                confidence=e.confidence,
                bbox={"ymin": int(e.bbox_ymin), "xmin": int(e.bbox_xmin), "ymax": int(e.bbox_ymax), "xmax": int(e.bbox_xmax)}
                if e.bbox_ymin is not None
                else None,
            )
            for e in doc.extractions
        ]
        line_items = [
            LineItemDetail(
                sku=item.sku,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
                bbox=item.bbox,
            )
            for item in doc.line_items
        ]
        docs_detail.append(
            DocumentDetail(
                id=doc.id,
                doc_type=doc.doc_type.value,
                file_path=doc.file_path,
                pages_count=len(doc.pages),
                extractions=extractions,
                line_items=line_items,
            )
        )

    # Detalle de reconciliacion
    reconcile_detail = None
    if dossier.reconciliation_results:
        rec = dossier.reconciliation_results[0]
        details = rec.discrepancy_details or {}
        reconcile_detail = ReconciliationDetail(
            math_valid=rec.math_valid,
            goods_matched=rec.goods_matched,
            payment_matched=rec.payment_matched,
            summary=details.get("summary", ""),
            discrepancies=details.get("discrepancies", []),
        )

    return DossierDetailResponse(
        id=dossier.id,
        title=dossier.title,
        status=dossier.status.value,
        created_at=dossier.created_at,
        documents=docs_detail,
        reconciliation=reconcile_detail,
    )


@router.get("/{dossier_id}/pages/{page_id}/image")
def get_page_image(dossier_id: UUID, page_id: UUID, db: Session = Depends(get_db)):
    """Retorna la imagen corregida y contrastada de una pagina para el visor interactivo con cajas SVG."""
    page = (
        db.query(DBDocumentPage)
        .join(DBDocument, DBDocumentPage.document_id == DBDocument.id)
        .filter(DBDocument.dossier_id == dossier_id, DBDocumentPage.id == page_id)
        .first()
    )
    if not page or not Path(page.image_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imagen de pagina no encontrada")

    return FileResponse(page.image_path, media_type="image/png")


@router.post("/search", response_model=SearchResponse)
def search_dossiers(search_req: SearchRequest, db: Session = Depends(get_db)):
    """Busqueda semantica vectorial en lenguaje natural sobre los expedientes contables."""
    results = search_service.search(
        db=db,
        query=search_req.query,
        limit=search_req.limit,
        doc_type=search_req.doc_type,
        status=search_req.status,
    )

    items = [
        SearchResultItem(
            page_id=r.page_id,
            document_id=r.document_id,
            dossier_id=r.dossier_id,
            dossier_title=r.dossier_title,
            dossier_status=r.dossier_status,
            doc_type=r.doc_type,
            similarity_score=r.similarity_score,
            image_url=f"/api/v1/dossiers/{r.dossier_id}/pages/{r.page_id}/image",
        )
        for r in results
    ]

    return SearchResponse(
        total_results=len(items),
        query=search_req.query,
        results=items,
    )
