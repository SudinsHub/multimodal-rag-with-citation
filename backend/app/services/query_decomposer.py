"""
Query Decomposer Service (Document-Agnostic).
Analyzes user questions to determine if multi-hop information retrieval or
mathematical/computational reasoning is required. Formulates targeted sub-queries.
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from providers.factory import get_llm

logger = logging.getLogger(__name__)


class DecompositionPlan(BaseModel):
    is_complex: bool = Field(
        default=False, 
        description="True if the question requires multi-parameter retrieval, tables, or calculations."
    )
    thought: str = Field(
        default="", 
        description="Reasoning on what parameters, rules, or formulas are needed from the document."
    )
    sub_queries: List[str] = Field(
        default_factory=list, 
        description="2 to 4 targeted, keyword-rich sub-queries to retrieve from the document."
    )
    calculation_needed: bool = Field(
        default=False, 
        description="True if deterministic arithmetic or dimensional computation is required."
    )


DECOMPOSITION_PROMPT = """You are an expert document research and reasoning assistant.
Your job is to analyze the user's question against their uploaded document and determine if answering it requires:
1. Multi-hop retrieval (combining separate rules, tables, or sections).
2. Mathematical, volumetric, engineering, financial, or statutory calculations.

DOCUMENT INFORMATION:
{document_info}

USER QUESTION:
{question}

INSTRUCTIONS:
- If the question is simple and single-fact (e.g. "Who wrote this?", "Define term X", "Summarize page 5"):
  Set "is_complex" to false, and "sub_queries" to a single query containing the question.
- If the question involves multiple parameters, design criteria, tables, formulas, or calculations:
  Set "is_complex" to true, provide a brief "thought" explaining what distinct pieces of data must be retrieved from the document, and break it down into 2 to 4 distinct, targeted "sub_queries".
- Do NOT assume any specific industry or building code unless the user question or document mentions it. Be completely document-agnostic.
- Return ONLY a valid JSON object matching this schema:
{{
  "is_complex": true/false,
  "thought": "Brief explanation of what parameters/rules/formulas must be retrieved",
  "sub_queries": ["sub query 1", "sub query 2", "sub query 3"],
  "calculation_needed": true/false
}}
"""


def decompose_query(
    query: str,
    document_title: Optional[str] = None,
    document_description: Optional[str] = None,
) -> DecompositionPlan:
    """
    Decomposes a user query into targeted sub-queries for multi-hop retrieval.
    Consumes exactly 1 LLM call.
    """
    doc_info = "Document: " + (document_title or "Uploaded Document")
    if document_description:
        doc_info += f" - Description: {document_description}"

    prompt = ChatPromptTemplate.from_template(DECOMPOSITION_PROMPT)
    llm = get_llm()

    chain = prompt | llm

    try:
        response = chain.invoke({
            "document_info": doc_info,
            "question": query,
        })
        content = response.content if hasattr(response, "content") else str(response)

        # Extract JSON from markdown fence if present
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            sub_queries = [str(q).strip() for q in data.get("sub_queries", []) if str(q).strip()]
            if not sub_queries:
                sub_queries = [query]

            return DecompositionPlan(
                is_complex=bool(data.get("is_complex", len(sub_queries) > 1)),
                thought=str(data.get("thought", "")),
                sub_queries=sub_queries[:4],  # Cap at max 4 sub-queries
                calculation_needed=bool(data.get("calculation_needed", False)),
            )
    except Exception as e:
        logger.warning(f"Query decomposition failed: {e}. Falling back to single query.")

    # Graceful fallback: treat as single query
    return DecompositionPlan(
        is_complex=False,
        thought="Direct document retrieval",
        sub_queries=[query],
        calculation_needed=False,
    )
