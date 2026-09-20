"""
Chat and RAG Query API endpoints.
Provides multi-session chat with citation-backed responses.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.db.models.chat import ChatSession, ChatMessage
from backend.app.db.models.document import Document
from backend.app.schemas.chat import (
    SessionCreate,
    SessionResponse,
    ChatMessageResponse,
    ChatQueryRequest,
    ChatQueryResponse,
)
from backend.app.schemas.citation import CitationProof
from backend.app.services.rag_orchestrator import execute_rag

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(db: Session = Depends(get_db)):
    """List all chat sessions ordered by latest updated."""
    return db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    """Create a new chat session."""
    if payload.document_id:
        doc = db.query(Document).filter(Document.id == payload.document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

    session = ChatSession(
        title=payload.title or "New Conversation",
        document_id=payload.document_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: UUID, db: Session = Depends(get_db)):
    """Get chat session metadata."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: UUID, db: Session = Depends(get_db)):
    """Delete a chat session and all its messages."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    db.delete(session)
    db.commit()
    return None


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
def get_session_messages(session_id: UUID, db: Session = Depends(get_db)):
    """Get all messages in a chat session."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()


@router.post("/sessions/{session_id}/messages", response_model=ChatQueryResponse)
def send_message(session_id: UUID, payload: ChatQueryRequest, db: Session = Depends(get_db)):
    """
    Send a message to the RAG pipeline within a session:
    1. Records user message
    2. Executes Hybrid Retrieval (pgvector + FTS with RRF)
    3. Generates LLM response with inline [Source N] citations
    4. Records assistant message with structured citation cards
    5. Updates session title automatically if first message
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    target_doc_id = payload.document_id or session.document_id

    # 1. Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=payload.message,
    )
    db.add(user_msg)
    db.commit()

    # Update session title if it's the default title
    if session.title == "New Conversation":
        snippet = payload.message.strip().replace("\n", " ")
        session.title = snippet[:40] + ("..." if len(snippet) > 40 else "")
        db.commit()

    # 2. Execute RAG pipeline
    rag_output = execute_rag(
        db=db,
        query=payload.message,
        document_id=target_doc_id,
    )

    citations_dicts = [c.model_dump() for c in rag_output["citations"]]

    # 3. Save assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=rag_output["answer"],
        citations=citations_dicts,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return ChatQueryResponse(
        session_id=session_id,
        message_id=assistant_msg.id,
        query=payload.message,
        answer=rag_output["answer"],
        citations=rag_output["citations"],
        num_sources=rag_output["num_sources"],
    )
