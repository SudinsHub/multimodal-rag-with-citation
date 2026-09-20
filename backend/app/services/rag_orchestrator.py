"""
RAG Orchestration service.
Prepares citation-forcing prompt context, invokes the LLM via the factory, and parses output.
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from langchain_core.prompts import ChatPromptTemplate
from backend.app.services.hybrid_retriever import search_hybrid
from backend.app.schemas.citation import CitationProof, BoundingBox
from backend.app.core.config import app_settings
from providers.factory import get_llm

CITATION_PROMPT_TEMPLATE = """You are a precise document search assistant. Your job is to answer questions based ONLY on the provided context from a PDF document.

CRITICAL RULES:
1. Every factual claim in your answer MUST have a citation in the format [Source N] where N matches the source number below.
2. If the context doesn't contain enough information to answer, say "The document does not contain sufficient information to answer this question."
3. Do NOT make up information or use knowledge outside the provided context.
4. After your answer, provide a CITATIONS section listing each source you used.

CONTEXT:
{context}

QUESTION: {question}

Provide your answer with inline [Source N] citations, followed by a CITATIONS section:"""

def format_context_with_sources(chunks: List[Dict[str, Any]]) -> str:
    formatted_parts = []
    for i, c in enumerate(chunks):
        pages = c.get("page_numbers", [])
        headings = c.get("headings", [])
        element_type = c.get("element_type", "text")
        header = f"[Source {i + 1}] (Page {pages}, Section: {' > '.join(headings) if headings else 'N/A'}, Type: {element_type})"
        formatted_parts.append(f"{header}\n{c['text']}")

    return "\n\n" + "---\n\n".join(formatted_parts)

def execute_rag(
    db: Session,
    query: str,
    document_id: Optional[UUID] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Run the end-to-end RAG pipeline:
    1. Retrieve candidates via hybrid search (pgvector + FTS with RRF)
    2. Format prompt context
    3. Generate response with inline [Source N]
    4. Compile structured citation proofs
    """
    retrieved_chunks = search_hybrid(
        db=db,
        query=query,
        document_id=document_id,
        top_k=top_k,
        bm25_weight=app_settings.BM25_WEIGHT,
        vector_weight=app_settings.VECTOR_WEIGHT,
    )

    if not retrieved_chunks:
        return {
            "query": query,
            "answer": "No relevant documents found. Please upload a document first.",
            "citations": [],
            "num_sources": 0,
        }

    context = format_context_with_sources(retrieved_chunks)
    prompt = ChatPromptTemplate.from_template(CITATION_PROMPT_TEMPLATE)
    llm = get_llm()

    chain = prompt | llm
    response = chain.invoke({"context": context, "question": query})
    answer_text = response.content if hasattr(response, 'content') else str(response)

    # Pre-fetch document titles for all cited document IDs
    doc_ids = set()
    for c in retrieved_chunks:
        did = c.get("document_id")
        if did:
            try:
                doc_ids.add(UUID(str(did)))
            except Exception:
                pass

    doc_titles: Dict[str, str] = {}
    if doc_ids:
        from backend.app.db.models.document import Document
        docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
        for d in docs:
            doc_titles[str(d.id)] = d.title or d.filename

    # Build structured citations
    citations: List[CitationProof] = []
    for i, c in enumerate(retrieved_chunks):
        raw_bboxes = c.get("bboxes", [])
        parsed_bboxes = [
            BoundingBox(
                l=float(b.get("l", 0.0)),
                t=float(b.get("t", 0.0)),
                r=float(b.get("r", 0.0)),
                b=float(b.get("b", 0.0)),
                coord_origin=b.get("coord_origin", "TOPLEFT"),
                page_width=b.get("page_width"),
                page_height=b.get("page_height"),
                l_pct=b.get("l_pct"),
                t_pct=b.get("t_pct"),
                w_pct=b.get("w_pct"),
                h_pct=b.get("h_pct"),
            )
            for b in raw_bboxes if isinstance(b, dict)
        ]

        text_content = c.get("text", "")
        excerpt = text_content[:250].replace("\n", " ") + ("..." if len(text_content) > 250 else "")

        real_doc_id = str(c.get("document_id")) if c.get("document_id") else (c.get("doc_id") or None)
        doc_title = doc_titles.get(real_doc_id) if real_doc_id else None

        citations.append(
            CitationProof(
                source_num=i + 1,
                page_numbers=c.get("page_numbers", []),
                bboxes=parsed_bboxes,
                headings=c.get("headings", []),
                element_type=c.get("element_type", "text"),
                text_excerpt=excerpt,
                chunk_id=str(c.get("id", "")),
                doc_id=real_doc_id,
                document_id=real_doc_id,
                document_title=doc_title,
            )
        )

    return {
        "query": query,
        "answer": answer_text,
        "citations": citations,
        "num_sources": len(citations),
    }
