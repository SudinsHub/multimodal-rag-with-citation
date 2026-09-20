"""
Chat and RAG query schemas.
"""

from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from backend.app.schemas.citation import CitationProof

class SessionCreate(BaseModel):
    title: Optional[str] = Field("New Conversation", max_length=255)
    document_id: Optional[UUID] = None

class SessionResponse(BaseModel):
    id: UUID
    title: str
    document_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChatMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    citations: Optional[List[CitationProof]] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True

class ChatQueryRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Question or search query")
    document_id: Optional[UUID] = Field(None, description="Optional target document filter")

class ChatQueryResponse(BaseModel):
    session_id: UUID
    message_id: UUID
    query: str
    answer: str
    citations: List[CitationProof] = Field(default_factory=list)
    num_sources: int
