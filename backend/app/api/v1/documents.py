"""
Document API endpoints.
Handles PDF upload with user-specified document details, ingestion, and management.
"""

import os
import uuid
import shutil
import logging
from typing import List, Optional
from uuid import UUID
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.app.db.session import get_db, SessionLocal
from backend.app.db.models.document import Document, DocumentChunk
from backend.app.db.models.user import User
from backend.app.schemas.document import DocumentResponse, ContentTypeOption
from backend.app.core.config import app_settings
from backend.app.core.auth import get_current_user
from backend.app.services.docling_extractor import extract_document
from backend.app.services.image_summarizer import summarize_images
from backend.app.services.chunker import chunk_document
from providers.factory import get_embeddings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])

def process_document_background(
    doc_id: UUID, 
    file_path: Path, 
    content_type: str, 
    chunk_max_tokens: int, 
    chunk_merge_peers: bool
):
    """Background task to run Docling extraction, VLM summarization, chunking, and embedding."""
    db: Session = SessionLocal()
    try:
        doc_record = db.query(Document).filter(Document.id == doc_id).first()
        if not doc_record:
            return

        doc_record.status = "processing"
        db.commit()

        # 1. Docling Extraction
        docling_doc, metadata = extract_document(file_path, content_type)
        doc_record.docling_metadata = metadata
        db.commit()

        # 2. Multimodal VLM summaries (if images enabled)
        image_summaries = summarize_images(docling_doc, content_type)

        # 3. Structure-aware chunking
        citation_chunks = chunk_document(
            docling_doc,
            max_tokens=chunk_max_tokens,
            merge_peers=chunk_merge_peers
        )

        # Merge image summaries into chunk list
        start_idx = len(citation_chunks)
        for i, img_chunk in enumerate(image_summaries):
            img_chunk["chunk_index"] = start_idx + i
            if "doc_id" not in img_chunk and citation_chunks:
                img_chunk["doc_id"] = citation_chunks[0].get("doc_id", "unknown")
            citation_chunks.append(img_chunk)

        # 4. Generate embeddings and store chunks
        embeddings_model = get_embeddings()
        texts = [c["text"] for c in citation_chunks if c["text"].strip()]
        
        # Batch embed
        vectors = embeddings_model.embed_documents(texts) if texts else []

        # Persist DocumentChunks
        chunk_objects = []
        vec_idx = 0
        for c in citation_chunks:
            if not c["text"].strip():
                continue
            
            chunk_obj = DocumentChunk(
                document_id=doc_id,
                chunk_index=c["chunk_index"],
                text=c["text"],
                embedding=vectors[vec_idx] if vec_idx < len(vectors) else None,
                page_numbers=c.get("page_numbers", []),
                bboxes=c.get("bboxes", []),
                headings=c.get("headings", []),
                element_type=c.get("element_type", "text"),
                doc_id=c.get("doc_id", "unknown"),
            )
            chunk_objects.append(chunk_obj)
            vec_idx += 1

        db.bulk_save_objects(chunk_objects)
        
        doc_record.status = "indexed"
        doc_record.chunk_count = len(chunk_objects)
        db.commit()
        logger.info(f"Successfully processed document {doc_id} with {len(chunk_objects)} chunks.")

    except Exception as e:
        logger.exception(f"Failed processing document {doc_id}: {e}")
        doc_record = db.query(Document).filter(Document.id == doc_id).first()
        if doc_record:
            doc_record.status = "failed"
            doc_record.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    content_type: ContentTypeOption = Form(ContentTypeOption.AUTO_DETECT),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    chunk_max_tokens: int = Form(512),
    chunk_merge_peers: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF document with custom extraction details.
    Content type options: auto_detect, text_only, tables, images, scanned, mixed.
    Scoped to current_user.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_id = uuid.uuid4()
    safe_filename = f"{file_id}_{file.filename}"
    saved_path = app_settings.UPLOAD_DIR / safe_filename

    # Save uploaded file
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(saved_path)

    # Create document record
    doc = Document(
        id=file_id,
        filename=file.filename,
        file_path=str(saved_path),
        file_size=file_size,
        content_type=content_type.value,
        title=title or file.filename,
        description=description,
        user_id=current_user.id,
        status="uploaded",
        chunk_count=0,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Trigger ingestion pipeline in background
    background_tasks.add_task(
        process_document_background,
        doc_id=doc.id,
        file_path=saved_path,
        content_type=content_type.value,
        chunk_max_tokens=chunk_max_tokens,
        chunk_merge_peers=chunk_merge_peers,
    )

    return doc


@router.get("", response_model=List[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all uploaded documents belonging to current user."""
    return db.query(Document).filter(Document.user_id == current_user.id).order_by(Document.created_at.desc()).all()


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single document details owned by current user."""
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document and its indexed chunks owned by current user."""
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove file from disk
    try:
        p = Path(doc.file_path)
        if p.exists():
            p.unlink()
    except Exception as e:
        logger.warning(f"Could not delete physical file: {e}")

    db.delete(doc)
    db.commit()
    return None


@router.get("/{document_id}/file")
def get_document_file(
    document_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Serve the raw PDF file for viewing/highlighting in browser (owned by current user)."""
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    p = Path(doc.file_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found on storage.")

    return FileResponse(
        path=str(p),
        filename=doc.filename,
        media_type="application/pdf"
    )
