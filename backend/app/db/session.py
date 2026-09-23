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
