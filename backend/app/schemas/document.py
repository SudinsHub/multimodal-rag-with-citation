"""
Document schemas for validation and serialization.
Supports content type options from rag_pipeline.ipynb.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class ContentTypeOption(str, Enum):
    AUTO_DETECT = "auto_detect"
    TEXT_ONLY = "text_only"
    TABLES = "tables"
    IMAGES = "images"
    SCANNED = "scanned"
    MIXED = "mixed"

class DocumentUploadDetails(BaseModel):
    content_type: ContentTypeOption = Field(
        default=ContentTypeOption.AUTO_DETECT,
        description="Extraction mode (auto_detect, text_only, tables, images, scanned, mixed)"
    )
    title: Optional[str] = Field(None, max_length=255, description="Friendly title or document label")
    description: Optional[str] = Field(None, description="Optional document notes or description")
    chunk_max_tokens: int = Field(512, ge=64, le=2048, description="Max tokens per chunk for HybridChunker")
    chunk_merge_peers: bool = Field(True, description="Merge small sibling chunks")

class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    file_size: int
    content_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    chunk_count: int
    docling_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentStats(BaseModel):
    total_documents: int
    indexed_documents: int
    total_chunks: int
