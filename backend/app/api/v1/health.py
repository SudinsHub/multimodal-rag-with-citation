"""
Health check and configuration inspection endpoint.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.db.session import get_db
from config.settings import settings

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def health_check(db: Session = Depends(get_db)):
    """Check database connection and active model provider settings."""
    db_status = "healthy"
    pgvector_installed = False
    try:
        res = db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector';")).fetchone()
        pgvector_installed = bool(res)
    except Exception as e:
        db_status = f"unhealthy: {e}"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": db_status,
        "pgvector_active": pgvector_installed,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "vlm_provider": settings.VLM_PROVIDER,
        "vlm_model": settings.VLM_MODEL,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
    }
