"""
Central configuration — loads .env and exposes typed settings.

Usage:
    from config.settings import settings
    print(settings.LLM_PROVIDER)  # "ollama"

Change the .env file to switch providers. Never edit this file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (works in Docker and natively)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class Settings:
    """Typed access to all .env configuration values."""

    # ── LLM ──────────────────────────────────────────────────
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3.2")

    # ── VLM (Vision / Multimodal) ────────────────────────────
    VLM_PROVIDER: str = os.getenv("VLM_PROVIDER", "ollama")
    VLM_MODEL: str = os.getenv("VLM_MODEL", "llava")

    # ── Embeddings ───────────────────────────────────────────
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "local")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    # ── API Keys ─────────────────────────────────────────────
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # ── Ollama ───────────────────────────────────────────────
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # ── Retrieval ────────────────────────────────────────────
    BM25_WEIGHT: float = float(os.getenv("BM25_WEIGHT", "0.4"))
    VECTOR_WEIGHT: float = float(os.getenv("VECTOR_WEIGHT", "0.6"))
    TOP_K: int = int(os.getenv("TOP_K", "5"))

    # ── Chunking ─────────────────────────────────────────────
    CHUNK_MAX_TOKENS: int = int(os.getenv("CHUNK_MAX_TOKENS", "512"))
    CHUNK_MERGE_PEERS: bool = os.getenv("CHUNK_MERGE_PEERS", "true").lower() == "true"

    # ── PDF Input ────────────────────────────────────────────
    PDF_PATH: str = os.getenv("PDF_PATH", "pdfs/sample.pdf")

    @property
    def resolved_pdf_path(self) -> Path:
        """Resolve PDF_PATH to an absolute Path (supporting relative to project root or absolute paths)."""
        p = Path(self.PDF_PATH)
        if p.is_absolute() and p.exists():
            return p
        root = Path(__file__).resolve().parent.parent
        resolved = (root / p).resolve()
        if resolved.exists():
            return resolved
        return p if p.is_absolute() else resolved

    def summary(self) -> str:
        """Return a human-readable summary of the active configuration."""
        pdf_display = self.PDF_PATH if len(self.PDF_PATH) <= 30 else "..." + self.PDF_PATH[-27:]
        lines = [
            "╔══════════════════════════════════════════════╗",
            "║       RAG Pipeline — Active Configuration     ║",
            "╠══════════════════════════════════════════════╣",
            f"║  📡 LLM:       {self.LLM_PROVIDER:>12} → {self.LLM_MODEL:<16} ║",
            f"║  👁️  VLM:       {self.VLM_PROVIDER:>12} → {self.VLM_MODEL:<16} ║",
            f"║  🧬 Embed:     {self.EMBEDDING_PROVIDER:>12} → {self.EMBEDDING_MODEL[-20:]:<16} ║",
            f"║  📄 PDF:       {pdf_display:<35} ║",
            f"║  ⚖️  Weights:   BM25={self.BM25_WEIGHT}  Vector={self.VECTOR_WEIGHT:<10} ║",
            f"║  📦 Top-K:     {self.TOP_K:<35} ║",
            f"║  ✂️  Chunk:     max_tokens={self.CHUNK_MAX_TOKENS}, merge={self.CHUNK_MERGE_PEERS}  ║",
            "╚══════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)


settings = Settings()
