"""
Guardrails and Security Service for Construction RAG.
Provides pre-flight PDF validation, input heuristic security scanning, 
jailbreak detection, and sliding-window rate limiting.
"""

import re
import time
from pathlib import Path
from typing import Optional, Dict, List
from collections import defaultdict
from fastapi import HTTPException, status
from pypdf import PdfReader
import logging

logger = logging.getLogger(__name__)

# Heuristic patterns for prompt injection, jailbreaking, and assistant abuse
JAILBREAK_PATTERNS = [
    re.compile(r"(?i)\b(ignore|disregard|forget|override|bypass)\s+(all\s+)?(previous|prior|above|system)\s+(instructions|prompts|rules|commands|constraints)"),
    re.compile(r"(?i)\b(you are now|act as|pretend to be|simulate)\s+(DAN|unrestricted|jailbreak|developer mode|ChatGPT|an evil|an unfiltered)"),
    re.compile(r"(?i)\b(reveal|show|print|output|display)\s+(your\s+)?(system\s+prompt|hidden\s+instructions|secret\s+instructions)"),
    re.compile(r"(?i)\b(system\s+message|system\s+override|prompt\s+injection)\b"),
    re.compile(r"(?i)\b(repeat\s+everything\s+above|echo\s+initial\s+prompt)\b"),
    re.compile(r"(?i)(<script|javascript:|eval\(|base64_decode)"),
]

# Obvious off-topic abusive/irrelevant intent patterns (e.g. asking to write ransomware, adult, etc.)
ABUSE_PATTERNS = [
    re.compile(r"(?i)\b(write\s+(a\s+)?(malware|keylogger|exploit|virus|ransomware))\b"),
    re.compile(r"(?i)\b(how\s+to\s+(hack|ddos|bypass\s+security))\b"),
]


def check_input_safety(query: str, max_chars: int = 600) -> Optional[str]:
    """
    Scans a user input query against length limits and heuristic jailbreak patterns.
    Returns an error message if unsafe, or None if the query passes inspection.
    """
    trimmed = query.strip()
    if not trimmed:
        return "Query cannot be empty."

    if len(trimmed) > max_chars:
        return f"Query is too long ({len(trimmed)} characters). The maximum allowed length is {max_chars} characters."

    for pattern in JAILBREAK_PATTERNS:
        if pattern.search(trimmed):
            logger.warning(f"Guardrail triggered: prompt injection attempt detected: '{trimmed[:80]}...'")
            return "Security Notice: Your query contains patterns that violate system safety rules. Please ask questions directly related to your uploaded document."

    for pattern in ABUSE_PATTERNS:
        if pattern.search(trimmed):
            logger.warning(f"Guardrail triggered: abusive query detected: '{trimmed[:80]}...'")
            return "Security Notice: Your query contains restricted content. Please ask legitimate questions about your document."

    return None


def validate_pdf_preflight(file_path: Path, max_pages: int = 50, max_file_size_mb: int = 10) -> int:
    """
    Fast pre-flight validation of a PDF file before heavy Docling processing:
    1. Checks file size
    2. Checks magic bytes (%PDF-)
    3. Uses pypdf to verify unencrypted status and page count (<= max_pages)
    Returns total page count on success. Raises HTTPException on failure.
    """
    # 1. File size check
    size_bytes = file_path.stat().st_size
    max_bytes = max_file_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {max_file_size_mb}MB (file is {size_bytes / (1024 * 1024):.1f}MB)."
        )

    # 2. Magic bytes verification
    with open(file_path, "rb") as f:
        header = f.read(5)
        if header != b"%PDF-":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format: File header is not a valid PDF document."
            )

    # 3. Fast pypdf validation
    try:
        reader = PdfReader(str(file_path))
        if reader.is_encrypted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Encrypted or password-protected PDFs are not supported."
            )
        
        page_count = len(reader.pages)
        if page_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded PDF contains 0 pages or no readable content."
            )

        if page_count > max_pages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document exceeds maximum limit of {max_pages} pages (uploaded file has {page_count} pages). To protect server resources on this free instance, please upload a document with {max_pages} or fewer pages."
            )

        return page_count

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"PDF preflight validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read PDF structure. The file may be damaged, password-protected, or in an unsupported format."
        )


class SlidingWindowRateLimiter:
    """Lightweight in-memory sliding window rate limiter."""
    def __init__(self):
        self._history: Dict[str, List[float]] = defaultdict(list)

    def check(self, key: str, max_requests: int, window_seconds: float) -> bool:
        """
        Returns True if request is allowed, False if rate limit is exceeded.
        Automatically prunes expired request timestamps.
        """
        now = time.time()
        cutoff = now - window_seconds
        
        # Prune old timestamps
        history = [ts for ts in self._history[key] if ts > cutoff]
        self._history[key] = history

        if len(history) >= max_requests:
            return False

        self._history[key].append(now)
        return True


rate_limiter = SlidingWindowRateLimiter()
