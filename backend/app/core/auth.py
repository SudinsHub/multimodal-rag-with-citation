"""
Authentication dependencies for FastAPI.
Validates Better Auth session tokens against PostgreSQL session table.
Supports both Cookie ('better-auth.session_token') and Bearer Authorization headers.
"""

from datetime import datetime
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.db.models.user import User, Session as UserSession

def extract_session_token(request: Request) -> Optional[str]:
    """Extract Better Auth session token from cookies or Authorization header."""
    # 1. Check Bearer token in Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            return token

    # 2. Check Better Auth cookies
    cookie_token = request.cookies.get("better-auth.session_token")
    if cookie_token:
        # In case the cookie value is signed with prefix (e.g. s:... or standard token)
        # Better Auth sets the token directly or signed; standard token is raw
        if "." in cookie_token and cookie_token.startswith("s:"):
            # strip express-style cookie signing if present
            cookie_token = cookie_token[2:].split(".")[0]
        return cookie_token

    # 3. Check secure cookie variant for HTTPS/production
    secure_cookie = request.cookies.get("__Secure-better-auth.session_token")
    if secure_cookie:
        if "." in secure_cookie and secure_cookie.startswith("s:"):
            secure_cookie = secure_cookie[2:].split(".")[0]
        return secure_cookie

    return None

def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return the authenticated user if a valid session exists, otherwise None."""
    token = extract_session_token(request)
    if not token:
        return None

    session_record = (
        db.query(UserSession)
        .filter(UserSession.token == token, UserSession.expires_at > datetime.utcnow())
        .first()
    )

    if not session_record or not session_record.user:
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
