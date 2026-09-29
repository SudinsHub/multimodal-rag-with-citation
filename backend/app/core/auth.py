"""
Authentication dependencies for FastAPI.
Validates Better Auth session tokens against PostgreSQL session table.
Supports both Cookie ('better-auth.session_token') and Bearer Authorization headers.
"""

from datetime import datetime, timezone
import logging
from typing import Optional
from urllib.parse import unquote
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.db.models.user import User, Session as UserSession

logger = logging.getLogger(__name__)


def clean_session_token(raw_token: str) -> str:
    """
    Clean and extract the raw session token from a cookie or header value.
    
    Better Auth signs cookies as `<token>.<signature>` (and URL-encodes it).
    Express-style signed cookies use `s:<token>.<signature>`.
    PostgreSQL stores the raw, un-signed alphanumeric token in the session table.
    """
    if not raw_token:
        return ""
    
    token = unquote(raw_token).strip().strip('"').strip("'")
    
    # Strip express-style prefix if present
    if token.startswith("s:"):
        token = token[2:]
        
    # Strip Better Auth HMAC signature suffix (.signature)
    if "." in token:
        token = token.split(".")[0]
        
    return token.strip()


def extract_session_token(request: Request) -> Optional[str]:
    """Extract Better Auth session token from cookies or Authorization header."""
    # 1. Check Bearer token in Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        cleaned = clean_session_token(token)
        if cleaned:
            return cleaned

    # 2. Check Better Auth cookies (standard & secure production prefix)
    for cookie_name in (
        "__Secure-better-auth.session_token",
        "better-auth.session_token",
    ):
        raw_cookie = request.cookies.get(cookie_name)
        if raw_cookie:
            cleaned = clean_session_token(raw_cookie)
            if cleaned:
                return cleaned

    return None


def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return the authenticated user if a valid session exists, otherwise None."""
    token = extract_session_token(request)
    if not token:
        return None

    # Compare expiry against database server time (func.now())
    session_record = (
        db.query(UserSession)
        .filter(
            UserSession.token == token,
            UserSession.expires_at > func.now(),
        )
        .first()
    )

    if not session_record or not session_record.user:
        logger.debug(f"No valid session record found for extracted token: {token[:8]}...")
        return None

    return session_record.user


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Dependency that requires an authenticated user; raises 401 if unauthenticated."""
    user = get_optional_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in to proceed.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

