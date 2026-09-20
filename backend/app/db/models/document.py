"""
Document and DocumentChunk database models with pgvector support.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, BigInteger, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from backend.app.db.base import Base
from backend.app.core.config import app_settings

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    
    # Document details specified at upload time
    content_type = Column(String(50), nullable=False, default="auto_detect")
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Status lifecycle
    status = Column(String(50), nullable=False, default="uploaded")
    error_message = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0)
    docling_metadata = Column(JSONB, nullable=True, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_documents_status", "status"),
        Index("idx_documents_created_at", "created_at"),
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    
    # Vector embedding using pgvector
    embedding = Column(Vector(app_settings.EMBEDDING_DIMENSION), nullable=True)
    
    # Rich Citation Provenance
    page_numbers = Column(JSONB, nullable=False, default=list)
    bboxes = Column(JSONB, nullable=False, default=list)
    headings = Column(JSONB, nullable=False, default=list)
    element_type = Column(String(50), nullable=False, default="text")
    doc_id = Column(String(128), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunks_doc_id", "document_id"),
        Index("idx_chunks_element_type", "element_type"),
    )
