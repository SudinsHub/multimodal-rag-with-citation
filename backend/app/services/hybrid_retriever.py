"""
Hybrid Retriever service combining pgvector cosine similarity and full-text keyword search via RRF.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.core.config import app_settings
from backend.app.db.models.document import Document, DocumentChunk
from providers.factory import get_embeddings

def search_hybrid(
    db: Session,
    query: str,
    document_id: Optional[UUID] = None,
    user_id: Optional[str] = None,
    top_k: int = 5,
    bm25_weight: float = 0.4,
    vector_weight: float = 0.6,
    rrf_k: int = 60,
) -> List[Dict[str, Any]]:
    """
    Perform Hybrid Retrieval (Dense Vector + Sparse Text) using PostgreSQL & pgvector with RRF fusion.
    Optionally scoped to specific document_id and/or user_id.
    """
    # 1. Embed query
    embeddings_model = get_embeddings()
    query_vector = embeddings_model.embed_query(query)
    vector_str = f"[{','.join(map(str, query_vector))}]"

    # Filter conditions
    filter_clauses = []
    params = {
        "query_vector": vector_str,
        "query_text": query,
        "limit": top_k * 3,
    }
    if document_id:
        filter_clauses.append("document_id = :doc_id")
        params["doc_id"] = str(document_id)
    if user_id:
        filter_clauses.append("document_id IN (SELECT id FROM documents WHERE user_id = :user_id)")
        params["user_id"] = str(user_id)

    filter_sql = ("AND " + " AND ".join(filter_clauses)) if filter_clauses else ""

    # 2. Vector search query
    vector_sql = f"""
        SELECT 
            id, 
            document_id, 
            chunk_index, 
            text, 
            page_numbers, 
            bboxes, 
            headings, 
            element_type, 
            doc_id,
            (embedding <=> :query_vector) AS distance
        FROM document_chunks
        WHERE embedding IS NOT NULL {filter_sql}
        ORDER BY distance ASC
        LIMIT :limit
    """
    vector_results = db.execute(text(vector_sql), params).fetchall()

    # 3. Sparse full-text search query
    text_sql = f"""
        SELECT 
            id, 
            document_id, 
            chunk_index, 
            text, 
            page_numbers, 
            bboxes, 
            headings, 
            element_type, 
            doc_id,
            ts_rank_cd(to_tsvector('english', text), plainto_tsquery('english', :query_text)) AS rank
        FROM document_chunks
        WHERE to_tsvector('english', text) @@ plainto_tsquery('english', :query_text) {filter_sql}
        ORDER BY rank DESC
        LIMIT :limit
    """
    try:
        text_results = db.execute(text(text_sql), params).fetchall()
    except Exception:
        # Fallback if query syntax or language issue occurs
        text_results = []

    # 4. Reciprocal Rank Fusion (RRF)
    rrf_scores: Dict[str, float] = {}
    chunk_map: Dict[str, Any] = {}

    # Dense rankings
    for rank, row in enumerate(vector_results):
        cid = str(row.id)
        chunk_map[cid] = row
        score = vector_weight * (1.0 / (rrf_k + (rank + 1)))
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + score

    # Sparse rankings
    for rank, row in enumerate(text_results):
        cid = str(row.id)
        if cid not in chunk_map:
            chunk_map[cid] = row
        score = bm25_weight * (1.0 / (rrf_k + (rank + 1)))
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + score

    # Fallback if both returned nothing (e.g. empty or purely random query)
    if not rrf_scores:
        fallback_query = db.query(DocumentChunk)
        if document_id:
            fallback_query = fallback_query.filter(DocumentChunk.document_id == document_id)
        if user_id:
            fallback_query = fallback_query.join(DocumentChunk.document).filter(Document.user_id == user_id)
        fallback_chunks = fallback_query.limit(top_k).all()
        return [
            {
                "id": str(c.id),
                "document_id": str(c.document_id),
                "text": c.text,
                "page_numbers": c.page_numbers or [],
                "bboxes": c.bboxes or [],
                "headings": c.headings or [],
                "element_type": c.element_type,
                "doc_id": c.doc_id,
                "score": 0.0,
            }
            for c in fallback_chunks
        ]

    # Sort candidates by combined RRF score
    sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)[:top_k]

    results: List[Dict[str, Any]] = []
    for cid in sorted_chunk_ids:
        row = chunk_map[cid]
        results.append({
            "id": str(row.id),
            "document_id": str(row.document_id),
            "chunk_index": row.chunk_index,
            "text": row.text,
            "page_numbers": row.page_numbers if isinstance(row.page_numbers, list) else [],
            "bboxes": row.bboxes if isinstance(row.bboxes, list) else [],
            "headings": row.headings if isinstance(row.headings, list) else [],
            "element_type": row.element_type,
            "doc_id": row.doc_id,
            "score": rrf_scores[cid],
        })

    return results
