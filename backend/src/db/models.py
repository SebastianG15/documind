import enum
import uuid
from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.db.base import Base


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING_OCR = "PROCESSING_OCR"
    EXTRACTING_VLM = "EXTRACTING_VLM"
    RECONCILING = "RECONCILING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DossierStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    DISCREPANCY_FOUND = "DISCREPANCY_FOUND"
    RECONCILED = "RECONCILED"


class DocumentType(str, enum.Enum):
    INVOICE = "INVOICE"
    SHIPPING_GUIDE = "SHIPPING_GUIDE"
    PAYMENT_VOUCHER = "PAYMENT_VOUCHER"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    UNKNOWN = "UNKNOWN"


class Dossier(Base):
    __tablename__ = "dossiers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    status = Column(Enum(DossierStatus), default=DossierStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    documents = relationship("Document", back_populates="dossier", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="dossier", cascade="all, delete-orphan")
    reconciliation_results = relationship("ReconciliationResult", back_populates="dossier", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dossier_id = Column(UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    progress_percent = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    dossier = relationship("Dossier", back_populates="jobs")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dossier_id = Column(UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(Enum(DocumentType), default=DocumentType.UNKNOWN, nullable=False)
    file_path = Column(String(1024), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dossier = relationship("Dossier", back_populates="documents")
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    extractions = relationship("Extraction", back_populates="document", cascade="all, delete-orphan")
    line_items = relationship("LineItem", back_populates="document", cascade="all, delete-orphan")


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    image_path = Column(String(1024), nullable=False)
    embedding = Column(Vector(384), nullable=True)

    document = relationship("Document", back_populates="pages")


class Extraction(Base):
    __tablename__ = "extractions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(100), nullable=False)
    field_value = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    bbox_ymin = Column(Float, nullable=True)
    bbox_xmin = Column(Float, nullable=True)
    bbox_ymax = Column(Float, nullable=True)
    bbox_xmax = Column(Float, nullable=True)

    document = relationship("Document", back_populates="extractions")


class LineItem(Base):
    __tablename__ = "line_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    sku = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    quantity = Column(Float, default=1.0, nullable=False)
    unit_price = Column(Float, default=0.0, nullable=False)
    line_total = Column(Float, default=0.0, nullable=False)
    bbox = Column(JSON, nullable=True)

    document = relationship("Document", back_populates="line_items")


class ReconciliationResult(Base):
    __tablename__ = "reconciliation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dossier_id = Column(UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False)
    math_valid = Column(Boolean, default=False, nullable=False)
    goods_matched = Column(Boolean, default=False, nullable=False)
    payment_matched = Column(Boolean, default=False, nullable=False)
    discrepancy_details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dossier = relationship("Dossier", back_populates="reconciliation_results")
