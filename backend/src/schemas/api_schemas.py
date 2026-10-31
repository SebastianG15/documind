from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    service: str = "DocuMind Financial AI API"


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Texto de busqueda semantica en lenguaje natural")
    limit: int = Field(default=10, ge=1, le=50)
    doc_type: Optional[str] = Field(default=None, description="Filtro opcional: INVOICE, SHIPPING_GUIDE, PAYMENT_VOUCHER")
    status: Optional[str] = Field(default=None, description="Filtro opcional: RECONCILED, DISCREPANCY_FOUND, PENDING")


class SearchResultItem(BaseModel):
    page_id: str
    document_id: str
    dossier_id: str
    dossier_title: str
    dossier_status: str
    doc_type: str
    similarity_score: float
    image_url: str


class SearchResponse(BaseModel):
    total_results: int
    query: str
    results: List[SearchResultItem]


class ExtractionItem(BaseModel):
    field_name: str
    field_value: str
    confidence: float
    bbox: Optional[Dict[str, int]] = None


class LineItemDetail(BaseModel):
    sku: Optional[str] = None
    description: str
    quantity: float
    unit_price: float
    line_total: float
    bbox: Optional[Dict[str, int]] = None


class DocumentDetail(BaseModel):
    id: UUID
    doc_type: str
    file_path: str
    pages_count: int
    extractions: List[ExtractionItem] = []
    line_items: List[LineItemDetail] = []


class ReconciliationDetail(BaseModel):
    math_valid: bool
    goods_matched: bool
    payment_matched: bool
    summary: str
    discrepancies: List[Dict[str, Any]] = []


class DossierDetailResponse(BaseModel):
    id: UUID
    title: str
    status: str
    created_at: datetime
    documents: List[DocumentDetail] = []
    reconciliation: Optional[ReconciliationDetail] = None


class DossierUploadResponse(BaseModel):
    dossier_id: UUID
    title: str
    status: str
    documents_processed: int
    reconciliation_summary: str
    math_valid: bool
    goods_matched: bool
    payment_matched: bool
