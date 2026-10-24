"""
Chat and RAG Query API endpoints.
Provides multi-session chat with citation-backed responses.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.db.models.chat import ChatSession, ChatMessage
from backend.app.db.models.document import Document
from backend.app.db.models.user import User
from backend.app.core.auth import get_current_user
from backend.app.schemas.chat import (
    SessionCreate,
    SessionResponse,
    ChatMessageResponse,
    ChatQueryRequest,
    ChatQueryResponse,
)
from backend.app.schemas.citation import CitationProof
from backend.app.services.rag_orchestrator import execute_rag
from backend.app.services.agentic_orchestrator import execute_agentic_rag, stream_agentic_rag
from backend.app.core.config import app_settings
from backend.app.core.guardrails import rate_limiter, check_input_safety
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all chat sessions belonging to current user ordered by latest updated."""
    return db.query(ChatSession).filter(ChatSession.user_id == current_user.id).order_by(ChatSession.updated_at.desc()).all()


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new chat session owned by current user."""
    if payload.document_id:
        doc = db.query(Document).filter(Document.id == payload.document_id, Document.user_id == current_user.id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

    session = ChatSession(
        title=payload.title or "New Conversation",
        document_id=payload.document_id,
        user_id=current_user.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get chat session metadata owned by current user."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chat session and all its messages owned by current user."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    db.delete(session)
    db.commit()
    return None


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
def get_session_messages(
    session_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all messages in a chat session owned by current user."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()


@router.post("/sessions/{session_id}/messages", response_model=ChatQueryResponse)
def send_message(
    session_id: UUID, 
    payload: ChatQueryRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message to the RAG pipeline within a session:
    1. Records user message
    2. Executes Hybrid Retrieval scoped by user_id
    3. Generates LLM response with inline [Source N] citations
    4. Records assistant message with structured citation cards
    5. Updates session title automatically if first message
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    target_doc_id = payload.document_id or session.document_id
    if target_doc_id:
        doc = db.query(Document).filter(Document.id == target_doc_id, Document.user_id == current_user.id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Target document not found or access denied.")

    # 1. Rate-limit check: 5 messages per minute
    if not rate_limiter.check(f"chat:{current_user.id}", max_requests=5, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit reached: Maximum 5 chat messages per minute. Please pause a moment before asking another question."
        )

    # 2. Input Heuristic Guard: check length and prompt injection / jailbreak patterns
    safety_violation = check_input_safety(payload.message, max_chars=app_settings.MAX_MESSAGE_LENGTH)
    if safety_violation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=safety_violation
        )

    # 3. User Prompt Quota: Max 10 prompts per session
    session_user_prompts = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.role == "user")
        .count()
    )
    if session_user_prompts >= app_settings.MAX_PROMPTS_PER_SESSION:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Session prompt limit reached: You can send at most {app_settings.MAX_PROMPTS_PER_SESSION} "
                "prompts in a single chat session. Please create a new chat session to continue."
            )
        )

    # 4. Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=payload.message,
    )
    db.add(user_msg)
    
    # Increment user's lifetime prompt count
    current_user.prompt_count = (current_user.prompt_count or 0) + 1
    db.commit()

    # Update session title if it's the default title
    if session.title == "New Conversation":
        snippet = payload.message.strip().replace("\n", " ")
        session.title = snippet[:40] + ("..." if len(snippet) > 40 else "")
        db.commit()

    # 5. Execute Agentic RAG pipeline scoped to current_user
    try:
        rag_output = execute_agentic_rag(
            db=db,
            query=payload.message,
            document_id=target_doc_id,
            user_id=current_user.id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error during RAG execution for session {session_id}: {e}")
        err_lower = str(e).lower()
        if "quota" in err_lower or "429" in err_lower or "resourceexhausted" in err_lower:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI service is temporarily experiencing high demand (rate quota reached). Please wait a moment and try asking again."
            )
        elif "safety" in err_lower or "blocked" in err_lower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The question could not be answered due to content safety guidelines. Please rephrase your query."
            )
        elif "api_key" in err_lower or "apikey" in err_lower:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI service is currently unavailable. Please contact the administrator or try again later."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to generate response at this time. Please try asking again shortly."
            )

    citations_dicts = [c.model_dump() for c in rag_output["citations"]]

    # 6. Save assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=rag_output["answer"],
        citations=citations_dicts,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    used_prompts = session_user_prompts + 1
    remaining_prompts = max(0, app_settings.MAX_PROMPTS_PER_SESSION - used_prompts)

    return ChatQueryResponse(
        session_id=session_id,
        message_id=assistant_msg.id,
        query=payload.message,
        answer=rag_output["answer"],
        citations=rag_output["citations"],
        num_sources=rag_output["num_sources"],
        thoughts=rag_output.get("thoughts", []),
        session_prompts_used=used_prompts,
        session_prompts_remaining=remaining_prompts,
        total_user_prompts=current_user.prompt_count,
    )


@router.post("/sessions/{session_id}/messages/stream")
def send_message_stream(
    session_id: UUID,
    payload: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stream agentic reasoning, status events, and the final response via Server-Sent Events (SSE).
    """
    # 1. Rate limiter
    if not rate_limiter.is_allowed(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before sending another query."
        )

    # 2. Input safety check
    is_safe, error_msg = check_input_safety(payload.message)
    if not is_safe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    # 3. Verify session
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    target_doc_id = payload.document_id or session.document_id
    if target_doc_id:
        doc = db.query(Document).filter(
            Document.id == target_doc_id,
            Document.user_id == current_user.id
        ).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Target document not found or access denied.")

    session_user_prompts = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.role == "user"
    ).count()

    if session_user_prompts >= app_settings.MAX_PROMPTS_PER_SESSION:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Session prompt limit reached ({app_settings.MAX_PROMPTS_PER_SESSION} max). Please create a new chat session."
        )

    # Save user message
    user_msg = ChatMessage(session_id=session_id, role="user", content=payload.message)
    db.add(user_msg)
    current_user.prompt_count = (current_user.prompt_count or 0) + 1
    if session.title == "New Conversation":
        snippet = payload.message.strip().replace("\n", " ")
        session.title = snippet[:40] + ("..." if len(snippet) > 40 else "")
    db.commit()

    def event_generator():
        try:
            for sse_chunk in stream_agentic_rag(
                db=db,
                query=payload.message,
                document_id=target_doc_id,
                user_id=current_user.id,
            ):
                # If this chunk is the final "done" event, persist assistant message
                if sse_chunk.startswith("event: done\n"):
                    try:
                        lines = sse_chunk.strip().split("\n")
                        data_line = next(l for l in lines if l.startswith("data: "))
                        done_payload = json.loads(data_line[6:])
                        answer_text = done_payload.get("answer", "")
                        citations = done_payload.get("citations", [])

                        assistant_msg = ChatMessage(
                            session_id=session_id,
                            role="assistant",
                            content=answer_text,
                            citations=citations,
                        )
                        db.add(assistant_msg)
                        db.commit()
                    except Exception as save_err:
                        logger.error(f"Failed to persist streamed assistant message: {save_err}")

                yield sse_chunk
        except Exception as e:
            logger.exception(f"Error in stream_agentic_rag: {e}")
            err_json = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {err_json}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

