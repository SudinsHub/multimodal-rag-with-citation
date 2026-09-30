"""
FastAPI Main Application.
Citation-Aware RAG Web Application Backend.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
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

# Global Exception Handlers to prevent system-level leaks
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Sanitize any accidental internal or SQL leaks in HTTP exceptions while preserving user notices."""
    detail = exc.detail
    if isinstance(detail, str):
        lower = detail.lower()
        if any(term in lower for term in ["relation \"", "table not found", "psycopg2", "syntax error at or near", "traceback"]):
            logger.warning(f"Sanitizing sensitive detail in HTTPException: {detail}")
            detail = "The database service is temporarily unavailable. Please try again shortly."
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail},
        headers=getattr(exc, "headers", None),
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format Pydantic schema validation errors into readable user guidance."""
    error_messages = []
    for error in exc.errors():
        loc = [str(l) for l in error.get("loc", []) if str(l) not in ("body", "query", "path")]
        field_name = ".".join(loc) if loc else "input"
        msg = error.get("msg", "Invalid value")
        error_messages.append(f"{field_name}: {msg}")
    
    friendly_msg = "Invalid input: " + "; ".join(error_messages) if error_messages else "Invalid request data."
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": friendly_msg},
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Prevent raw database exceptions (e.g. table not found, connection refused) from leaking to client."""
    logger.exception(f"Database error during request to {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "The database service is temporarily unavailable. Please try again in a few moments."},
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all unhandled exceptions; logs full stack trace and returns a polished message."""
    logger.exception(f"Unhandled server exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred while processing your request. Please try again shortly."},
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
