"""
Database session management and engine initialization.
Ensures the pgvector extension is enabled upon connection.
"""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from backend.app.core.config import app_settings

# Create standard sync engine for SQLAlchemy
engine = create_engine(
    app_settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Ensure vector extension is available and create all tables."""
    with engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        connection.commit()
    
    from backend.app.db.base import Base
    # import models to register with Base
    import backend.app.db.models.document  # noqa
    import backend.app.db.models.chat      # noqa
    
    Base.metadata.create_all(bind=engine)

def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
