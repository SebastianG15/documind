from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Document, DocumentPage, DocumentType, Dossier, DossierStatus
from src.nlp.embeddings import EmbeddingEngine


@dataclass
class SearchResult:
    page_id: str
    document_id: str
    dossier_id: str
    dossier_title: str
    dossier_status: str
    doc_type: str
    similarity_score: float
    image_path: str


class SemanticSearchService:
    """Servicio de busqueda vectorial y semantica hibrida para expedientes contables."""

    def __init__(self, embedding_engine: Optional[EmbeddingEngine] = None) -> None:
        self.embedding_engine = embedding_engine or EmbeddingEngine()

    def search(
        self,
        db: Session,
        query: str,
        limit: int = 10,
        doc_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[SearchResult]:
        query_vector = self.embedding_engine.embed_text(query)
        distance_expr = DocumentPage.embedding.cosine_distance(query_vector)

        stmt = (
            select(
                DocumentPage.id.label("page_id"),
                DocumentPage.image_path,
                Document.id.label("document_id"),
                Document.doc_type,
                Dossier.id.label("dossier_id"),
                Dossier.title.label("dossier_title"),
                Dossier.status.label("dossier_status"),
                (1.0 - distance_expr).label("similarity_score"),
            )
            .join(Document, DocumentPage.document_id == Document.id)
            .join(Dossier, Document.dossier_id == Dossier.id)
        )

        if doc_type:
            stmt = stmt.where(Document.doc_type == DocumentType(doc_type.upper()))

        if status:
            stmt = stmt.where(Dossier.status == DossierStatus(status.upper()))

        stmt = stmt.order_by(distance_expr).limit(limit)

        rows = db.execute(stmt).all()

        results: List[SearchResult] = []
        for r in rows:
            results.append(
                SearchResult(
                    page_id=str(r.page_id),
                    document_id=str(r.document_id),
                    dossier_id=str(r.dossier_id),
                    dossier_title=str(r.dossier_title),
                    dossier_status=r.dossier_status.value if hasattr(r.dossier_status, "value") else str(r.dossier_status),
                    doc_type=r.doc_type.value if hasattr(r.doc_type, "value") else str(r.doc_type),
                    similarity_score=round(float(r.similarity_score), 4),
                    image_path=str(r.image_path),
                )
            )

        return results
