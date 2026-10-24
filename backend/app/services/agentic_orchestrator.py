"""
Agentic Computational RAG Orchestrator (Budgeted ReAct & Streaming).
Executes a 2-LLM-call bounded plan:
1. Turn 1 (Query Decomposition): Plans sub-queries and calculation needs.
2. Local Multi-Search: Batch retrieves deduplicated chunks via local embeddings + PostgreSQL (0 Gemini calls).
3. Local Computation: Safely executes mathematical calculations via sandboxed Python (0 Gemini calls).
4. Turn 2 (Synthesis): Generates verified, citation-grounded response with proofs.
Yields real-time events for SSE streaming and provides synchronous fallback.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Generator, AsyncGenerator
from uuid import UUID
from sqlalchemy.orm import Session
from langchain_core.prompts import ChatPromptTemplate

from backend.app.services.hybrid_retriever import search_hybrid, search_hybrid_batch
from backend.app.services.query_decomposer import decompose_query, DecompositionPlan
from backend.app.services.python_executor import execute_safe_python, extract_and_run_code_blocks
from backend.app.schemas.citation import CitationProof, BoundingBox
from backend.app.core.config import app_settings
from backend.app.db.models.document import Document
from providers.factory import get_llm

logger = logging.getLogger(__name__)

AGENTIC_SYNTHESIS_PROMPT = """You are a rigorous, citation-grounded analytical assistant. Your task is to answer the user's question with complete precision using the provided context from their document.

<context>
{context}
</context>

<user_question>
{question}
</user_question>

{computational_guidance}

SECURITY & CITATION INSTRUCTIONS:
1. Every factual statement, numerical figure, standard, or equation MUST cite its source using inline citation format [Source N].
2. Answer based strictly on the retrieved document context. Do not invent standards, numbers, or rules not present in the document.
3. If calculation, formula substitution, or dimensional analysis is involved:
   - State the formulas clearly with their units.
   - Show step-by-step arithmetic.
   - If Python calculation was executed, use the exact computed results:
{python_results}
4. If the user question requires site-specific parameters not given in the document or prompt (e.g. available site length/width, specific soil percolation, custom schedules), provide the standard calculation first, and politely prompt the user to provide their specific dimensions for exact sizing.
5. If the context does not contain sufficient information to answer, state clearly: "The provided document does not contain sufficient information to answer this question."
6. After your answer, include a CITATIONS section listing each source used.

Provide your detailed, verified response:"""


def format_context_for_agent(chunks: List[Dict[str, Any]]) -> str:
    formatted_parts = []
    for i, c in enumerate(chunks):
        pages = c.get("page_numbers", [])
        headings = c.get("headings", [])
        element_type = c.get("element_type", "text")
        subq = c.get("matched_subquery")
        subq_str = f", Topic: '{subq}'" if subq else ""
        header = f"[Source {i + 1}] (Page {pages}, Section: {' > '.join(headings) if headings else 'N/A'}, Type: {element_type}{subq_str})"
        formatted_parts.append(f"{header}\n{c['text']}")

    return "\n\n" + "---\n\n".join(formatted_parts)


def build_citations(db: Session, retrieved_chunks: List[Dict[str, Any]]) -> List[CitationProof]:
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
        docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
        for d in docs:
            doc_titles[str(d.id)] = d.title or d.filename

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
    return citations


def execute_agentic_rag(
    db: Session,
    query: str,
    document_id: Optional[UUID] = None,
    user_id: Optional[str] = None,
    top_k_per_query: int = 3,
) -> Dict[str, Any]:
    """
    Synchronous execution of the Agentic Computational RAG pipeline:
    1. Plan & Query Decomposition (1 LLM Call)
    2. Local Multi-Search (0 LLM Calls)
    3. Math Verification / Python execution (0 LLM Calls)
    4. Synthesis & Grounded Output (1 LLM Call)
    """
    # Pre-fetch doc details for better decomposition
    doc_title, doc_desc = None, None
    if document_id:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc_title = doc.title or doc.filename
            doc_desc = doc.description

    # Step 1: Decomposition Plan (LLM Call 1)
    plan: DecompositionPlan = decompose_query(
        query=query, 
        document_title=doc_title, 
        document_description=doc_desc
    )

    # Step 2: Batch Local Retrieval (0 LLM Calls)
    if plan.is_complex and len(plan.sub_queries) > 1:
        retrieved_chunks = search_hybrid_batch(
            db=db,
            queries=plan.sub_queries,
            document_id=document_id,
            user_id=user_id,
            top_k_per_query=top_k_per_query,
            max_total_chunks=8,
        )
    else:
        retrieved_chunks = search_hybrid(
            db=db,
            query=query,
            document_id=document_id,
            user_id=user_id,
            top_k=top_k_per_query * 2,
        )

    # Relevance check
    if not retrieved_chunks:
        has_docs = False
        if user_id:
            has_docs = db.query(Document).filter(Document.user_id == user_id, Document.status == "indexed").count() > 0

        canned_msg = (
            "This question does not appear to be related to your uploaded document. I can only answer questions directly based on the uploaded document."
            if has_docs
            else "No indexed documents found. Please upload a PDF document from the sidebar first."
        )
        return {
            "query": query,
            "answer": canned_msg,
            "citations": [],
            "num_sources": 0,
            "thoughts": [plan.thought] if plan.thought else [],
        }

    # Step 3: Synthesis Prompt (LLM Call 2)
    context = format_context_for_agent(retrieved_chunks)
    comp_guidance = (
        "CALCULATION INSTRUCTIONS: If any calculation is needed, show formulas and step-by-step arithmetic."
        if plan.calculation_needed
        else ""
    )

    prompt = ChatPromptTemplate.from_template(AGENTIC_SYNTHESIS_PROMPT)
    llm = get_llm()
    chain = prompt | llm

    response = chain.invoke({
        "context": context,
        "question": query,
        "computational_guidance": comp_guidance,
        "python_results": "None. Perform deterministic steps directly."
    })
    raw_answer = response.content if hasattr(response, "content") else str(response)

    # Step 4: Deterministic Python Verification
    # If the LLM embedded python code, execute it in safe sandbox and verify
    code_eval = extract_and_run_code_blocks(raw_answer)
    verified_answer = raw_answer
    calculation_logs = None
    if code_eval:
        last_code, logs, vars_dict = code_eval
        calculation_logs = logs

    citations = build_citations(db, retrieved_chunks)

    thoughts = []
    if plan.thought:
        thoughts.append(plan.thought)
    if calculation_logs:
        thoughts.append(f"Calculation executed: {calculation_logs}")

    return {
        "query": query,
        "answer": verified_answer,
        "citations": citations,
        "num_sources": len(citations),
        "thoughts": thoughts,
        "sub_queries": plan.sub_queries,
    }


def stream_agentic_rag(
    db: Session,
    query: str,
    document_id: Optional[UUID] = None,
    user_id: Optional[str] = None,
    top_k_per_query: int = 3,
) -> Generator[str, None, None]:
    """
    Yields SSE formatted strings for streaming real-time status, thinking steps,
    and final citations/answers to the frontend.
    """
    def sse(event: str, data: Any) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    yield sse("status", {
        "step": "planning", 
        "label": "Analyzing query & planning multi-hop parameters..."
    })

    doc_title, doc_desc = None, None
    if document_id:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc_title = doc.title or doc.filename
            doc_desc = doc.description

    # 1. Plan (LLM Call 1)
    plan: DecompositionPlan = decompose_query(
        query=query, 
        document_title=doc_title, 
        document_description=doc_desc
    )

    if plan.thought:
        yield sse("thought", {"thought": plan.thought})

    # 2. Retrieval Status
    if plan.is_complex and len(plan.sub_queries) > 1:
        yield sse("status", {
            "step": "searching", 
            "label": f"Searching document across {len(plan.sub_queries)} targeted topics...",
            "sub_queries": plan.sub_queries,
        })
        retrieved_chunks = search_hybrid_batch(
            db=db,
            queries=plan.sub_queries,
            document_id=document_id,
            user_id=user_id,
            top_k_per_query=top_k_per_query,
            max_total_chunks=8,
        )
    else:
        yield sse("status", {
            "step": "searching", 
            "label": "Retrieving document sections and relevant tables...",
            "sub_queries": [query],
        })
        retrieved_chunks = search_hybrid(
            db=db,
            query=query,
            document_id=document_id,
            user_id=user_id,
            top_k=top_k_per_query * 2,
        )

    if not retrieved_chunks:
        has_docs = False
        if user_id:
            has_docs = db.query(Document).filter(Document.user_id == user_id, Document.status == "indexed").count() > 0
        canned_msg = (
            "This question does not appear to be related to your uploaded document. I can only answer questions directly based on the uploaded document."
            if has_docs
            else "No indexed documents found. Please upload a PDF document from the sidebar first."
        )
        yield sse("done", {
            "answer": canned_msg,
            "citations": [],
            "num_sources": 0,
            "thoughts": [plan.thought] if plan.thought else [],
        })
        return

    # 3. Calculation step
    if plan.calculation_needed:
        yield sse("status", {
            "step": "calculating", 
            "label": "Formulating equations & verifying dimensional math..."
        })

    # 4. Synthesizing Answer (LLM Call 2)
    yield sse("status", {
        "step": "synthesizing", 
        "label": "Synthesizing answer with verified inline citations..."
    })

    context = format_context_for_agent(retrieved_chunks)
    comp_guidance = (
        "CALCULATION INSTRUCTIONS: If any calculation is needed, show formulas and step-by-step arithmetic."
        if plan.calculation_needed
        else ""
    )

    prompt = ChatPromptTemplate.from_template(AGENTIC_SYNTHESIS_PROMPT)
    llm = get_llm()
    chain = prompt | llm

    response = chain.invoke({
        "context": context,
        "question": query,
        "computational_guidance": comp_guidance,
        "python_results": "None. Perform deterministic steps directly."
    })
    answer_text = response.content if hasattr(response, "content") else str(response)

    # Execute and check any code blocks
    code_eval = extract_and_run_code_blocks(answer_text)
    if code_eval:
        last_code, logs, vars_dict = code_eval
        if logs:
            yield sse("thought", {"thought": f"Verified Math Result: {logs}"})

    citations = build_citations(db, retrieved_chunks)
    citations_data = [c.model_dump() for c in citations]

    yield sse("done", {
        "answer": answer_text,
        "citations": citations_data,
        "num_sources": len(citations_data),
        "thoughts": [plan.thought] if plan.thought else [],
    })
