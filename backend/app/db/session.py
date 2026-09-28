"""
Database session management and engine initialization.
Ensures the pgvector extension is enabled upon connection.
"""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from backend.app.core.config import app_settings

def _resolve_database_url(url: str) -> str:
    """
    Ensure the database URL has a valid driver prefix compatible with installed packages.
    Handles 'postgres://' -> 'postgresql://', and auto-swaps between 'psycopg' (v3)
    and 'psycopg2' depending on what is installed in the current environment.
    """
    if not url:
        return url

    normalized = url.strip()
    if normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql://", 1)

    has_psycopg3 = False
    try:
        import psycopg  # noqa: F401
        has_psycopg3 = True
    except ImportError:
        pass

    has_psycopg2 = False
    try:
        import psycopg2  # noqa: F401
        has_psycopg2 = True
    except ImportError:
        pass

    # If postgresql+psycopg:// is specified but psycopg3 is missing, fall back to psycopg2
    if normalized.startswith("postgresql+psycopg://") and not has_psycopg3 and has_psycopg2:
        normalized = normalized.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
    # If postgresql+psycopg2:// is specified but psycopg2 is missing, fall back to psycopg3
    elif normalized.startswith("postgresql+psycopg2://") and not has_psycopg2 and has_psycopg3:
        normalized = normalized.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    # If generic postgresql:// is specified but only psycopg3 is installed, use postgresql+psycopg://
    elif normalized.startswith("postgresql://") and not has_psycopg2 and has_psycopg3:
        normalized = normalized.replace("postgresql://", "postgresql+psycopg://", 1)

    return normalized

# Create standard sync engine for SQLAlchemy with driver-compatible URL
db_url = _resolve_database_url(app_settings.DATABASE_URL)
engine_kwargs = {"pool_pre_ping": True}
if "sqlite" not in db_url:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(
    db_url,
    **engine_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Ensure vector extension is available, create all tables, and run safe migrations."""
    with engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        connection.commit()
    
    from backend.app.db.base import Base
    # import models to register with Base
    import backend.app.db.models.user      # noqa
    import backend.app.db.models.document  # noqa
    import backend.app.db.models.chat      # noqa
    
    Base.metadata.create_all(bind=engine)

    # Safe column additions if tables already existed
    with engine.connect() as connection:
        connection.execute(text("""
            DO $$ 
            BEGIN 
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documents') THEN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'user_id') THEN
                        ALTER TABLE documents ADD COLUMN user_id TEXT;
                        CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
                    END IF;
                END IF;

                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chat_sessions') THEN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chat_sessions' AND column_name = 'user_id') THEN
                        ALTER TABLE chat_sessions ADD COLUMN user_id TEXT;
                        CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
                    END IF;
                END IF;
            END $$;
        """))
        connection.commit()

def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
