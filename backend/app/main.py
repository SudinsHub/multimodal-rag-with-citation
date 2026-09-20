"""
FastAPI Main Application.
Citation-Aware RAG Web Application Backend.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import app_settings
from backend.app.api.v1.router import api_v1_router
from backend.app.db.session import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rag_app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event: initialize database schema and extensions on startup."""
    logger.info("Initializing database and pgvector extension...")
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.warning(
            f"Database auto-init deferred (DB may still be starting or unreachable): {e}"
        )
    yield
    logger.info("Application shutting down.")

app = FastAPI(
    title=app_settings.PROJECT_NAME,
    description="Multimodal Citation-Aware RAG Backend with PostgreSQL + pgvector and Hybrid Search",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_v1_router)

@app.get("/")
def root():
    return {
        "app": app_settings.PROJECT_NAME,
        "docs": "/docs",
        "api": "/api/v1",
        "status": "online",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
