"""
DocumentChunk schemas.
"""

from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from backend.app.schemas.citation import BoundingBox

class ChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    text: str
    page_numbers: List[int] = []
    bboxes: List[BoundingBox] = []
    headings: List[str] = []
    element_type: str
    doc_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
