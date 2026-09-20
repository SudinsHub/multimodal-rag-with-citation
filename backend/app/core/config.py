"""
Core Configuration module for the FastAPI RAG backend.
Extends and integrates with the root settings while providing typed web-app settings.
"""

import os
from pathlib import Path
from typing import List, Union
import json
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

# Locate project root and load .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

class AppSettings(BaseSettings):
    PROJECT_NAME: str = "Construction RAG 2.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgrespassword@localhost:5432/construction_rag"
    )
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))
    
    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("CORS_ORIGINS", mode="after")
    def parse_cors(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [x.strip() for x in v.split(",") if x.strip()]
        return v
    
    # Storage
    UPLOAD_DIR: Path = PROJECT_ROOT / "data" / "uploads"
    DOCSTORE_DIR: Path = PROJECT_ROOT / "data" / "docstore"

    # Default RAG settings
    BM25_WEIGHT: float = float(os.getenv("BM25_WEIGHT", "0.4"))
    VECTOR_WEIGHT: float = float(os.getenv("VECTOR_WEIGHT", "0.6"))
    TOP_K: int = int(os.getenv("TOP_K", "5"))
    CHUNK_MAX_TOKENS: int = int(os.getenv("CHUNK_MAX_TOKENS", "512"))
    CHUNK_MERGE_PEERS: bool = os.getenv("CHUNK_MERGE_PEERS", "true").lower() == "true"

    class Config:
        case_sensitive = True

app_settings = AppSettings()
app_settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app_settings.DOCSTORE_DIR.mkdir(parents=True, exist_ok=True)
