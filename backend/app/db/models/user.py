"""
User and Session database models matching Better Auth schema in PostgreSQL.
"""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.db.base import Base

class User(Base):
    __tablename__ = "user"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    email_verified = Column("emailVerified", Boolean, default=False, nullable=False)
    image = Column(String, nullable=True)
    created_at = Column("createdAt", DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column("updatedAt", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "session"

    id = Column(String, primary_key=True)
    user_id = Column("userId", String, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column("expiresAt", DateTime, nullable=False)
    ip_address = Column("ipAddress", String, nullable=True)
    user_agent = Column("userAgent", String, nullable=True)
    created_at = Column("createdAt", DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column("updatedAt", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("idx_session_token", "token"),
        Index("idx_session_user_id", "userId"),
    )
