"""
Server-side CLI utility to import an externally ingested document (e.g. from Kaggle/Colab)
directly into PostgreSQL & pgvector, matching the production schema and storage layout.

Usage:
    python -m backend.scripts.import_external_doc \\
        --json-file /path/to/book_export.json.gz \\
        --pdf-file /path/to/client_book.pdf \\
        --user-email client@example.com \\
        --title "Structural Engineering Handbook"
"""

import os
import sys
import uuid
import gzip
import json
import shutil
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Setup path and logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("import_external_doc")

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def import_document(
    json_path: Path,
    pdf_path: Path,
    user_email: str = None,
    user_id: str = None,
    custom_title: str = None,
    batch_size: int = 500,
):
    if not json_path.exists():
        raise FileNotFoundError(f"Export JSON not found at: {json_path}")
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    # 1. Read exported data
    logger.info(f"Loading export file: {json_path}")
    if json_path.suffix == ".gz" or str(json_path).endswith(".json.gz"):
        with gzip.open(json_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
    else:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    doc_meta = data.get("document", {})
    chunks_data = data.get("chunks", [])

    if not chunks_data:
        raise ValueError("Export JSON contains 0 chunks. Cannot import empty document.")

    logger.info(f"Loaded {len(chunks_data)} chunks from export.")

    from backend.app.core.config import app_settings
    from backend.app.db.session import SessionLocal
    from backend.app.db.models.document import Document, DocumentChunk
    from backend.app.db.models.user import User

    db = SessionLocal()
    try:
        # 2. Resolve User (or Pre-Provision if logging in later via Google)
        target_user = None
        if user_email:
            clean_email = user_email.strip().lower()
            target_user = db.query(User).filter(User.email == clean_email).first()
            if not target_user:
                # Pre-provision the user record in Better Auth schema so when they log in via Google,
                # Better Auth automatically matches their email to this existing user!
                new_user_id = str(uuid.uuid4())
                user_name = clean_email.split("@")[0].replace(".", " ").replace("_", " ").title()
                logger.info(f"User '{clean_email}' has not logged in yet. Pre-creating user account (ID: {new_user_id})...")
                target_user = User(
                    id=new_user_id,
                    name=user_name,
                    email=clean_email,
                    email_verified=True,
                    prompt_count=0,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(target_user)
                db.commit()
                db.refresh(target_user)
                logger.info(f"Successfully pre-provisioned user '{clean_email}'. When they sign in via Google OAuth, they will immediately see this document.")
        elif user_id:
            target_user = db.query(User).filter(User.id == user_id.strip()).first()
            if not target_user:
                raise ValueError(f"No user found with user_id: '{user_id}'. Please verify the user exists.")
        else:
            # Fallback to the first user in the database, or create a placeholder
            target_user = db.query(User).first()
            if not target_user:
                raise ValueError("No users found in database. Please pass --user-email to associate this document.")
            logger.warning(f"No user specified. Defaulting to first user: {target_user.email} (ID: {target_user.id})")

        assigned_user_id = target_user.id
        logger.info(f"Associating document with user: {target_user.name} ({target_user.email}, ID: {assigned_user_id})")

        # 3. Prepare Storage & Copy PDF
        app_settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        doc_id = uuid.uuid4()
        pdf_ext = pdf_path.suffix.lower() or ".pdf"
        dest_filename = f"{doc_id}{pdf_ext}"
        dest_pdf_path = app_settings.UPLOAD_DIR / dest_filename

        logger.info(f"Copying PDF file to server storage: {dest_pdf_path}")
        shutil.copyfile(pdf_path, dest_pdf_path)
        file_size = os.path.getsize(dest_pdf_path)

        doc_title = custom_title or doc_meta.get("title") or pdf_path.stem
        filename = doc_meta.get("filename") or pdf_path.name
        content_type = doc_meta.get("content_type", "mixed")
        docling_metadata = doc_meta.get("docling_metadata", {})

        # 4. Insert Document record
        logger.info(f"Creating Document record in database (ID: {doc_id})...")
        document_record = Document(
            id=doc_id,
            filename=filename,
            file_path=str(dest_pdf_path),
            file_size=file_size,
            content_type=content_type,
            title=doc_title,
            description=doc_meta.get("description", f"Imported large document ({len(chunks_data)} chunks)"),
            user_id=assigned_user_id,
            status="indexed",
            chunk_count=len(chunks_data),
            docling_metadata=docling_metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(document_record)
        db.commit()

        # 5. Insert DocumentChunk records in batches
        logger.info(f"Inserting {len(chunks_data)} chunks into 'document_chunks' table in batches of {batch_size}...")
        total_chunks = len(chunks_data)
        
        for start_idx in range(0, total_chunks, batch_size):
            end_idx = min(start_idx + batch_size, total_chunks)
            chunk_batch = chunks_data[start_idx:end_idx]
            
            chunk_objects = []
            for c in chunk_batch:
                text_content = c.get("text", "").strip()
                if not text_content:
                    continue

                chunk_obj = DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=doc_id,
                    chunk_index=c.get("chunk_index", 0),
                    text=text_content,
                    embedding=c.get("embedding"),
                    page_numbers=c.get("page_numbers", []),
                    bboxes=c.get("bboxes", []),
                    headings=c.get("headings", []),
                    element_type=c.get("element_type", "text"),
                    doc_id=str(doc_id),
                    created_at=datetime.utcnow(),
                )
                chunk_objects.append(chunk_obj)

            if chunk_objects:
                db.bulk_save_objects(chunk_objects)
                db.commit()
            
            logger.info(f"  -> Imported chunks {start_idx + 1} to {end_idx} of {total_chunks}")

        logger.info(f"Successfully imported document '{doc_title}' ({doc_id}) with {total_chunks} chunks!")
        logger.info("Running VACUUM ANALYZE on document_chunks...")
        try:
            from sqlalchemy import text
            db.execute(text("VACUUM ANALYZE document_chunks;"))
            db.commit()
        except Exception as e:
            logger.debug(f"VACUUM notice: {e}")

        logger.info(f"Done! The document is now ready for querying in the web application.")

    except Exception as e:
        db.rollback()
        logger.exception(f"Import failed: {e}")
        # Clean up copied file if error occurred
        if 'dest_pdf_path' in locals() and dest_pdf_path.exists():
            try:
                dest_pdf_path.unlink()
            except Exception:
                pass
        raise
    finally:
        db.close()


def reassign_document(doc_identifier: str, user_email: str = None, user_id: str = None):
    """Reassigns an existing document to a new user by email or user_id."""
    from backend.app.db.session import SessionLocal
    from backend.app.db.models.document import Document
    from backend.app.db.models.user import User

    db = SessionLocal()
    try:
        doc = None
        try:
            val_uuid = uuid.UUID(doc_identifier)
            doc = db.query(Document).filter(Document.id == val_uuid).first()
        except Exception:
            pass

        if not doc:
            doc = db.query(Document).filter(Document.title.ilike(f"%{doc_identifier}%")).first()

        if not doc:
            raise ValueError(f"Document matching '{doc_identifier}' not found in database.")

        target_user = None
        if user_email:
            clean_email = user_email.strip().lower()
            target_user = db.query(User).filter(User.email == clean_email).first()
            if not target_user:
                new_user_id = str(uuid.uuid4())
                user_name = clean_email.split("@")[0].replace(".", " ").replace("_", " ").title()
                target_user = User(
                    id=new_user_id,
                    name=user_name,
                    email=clean_email,
                    email_verified=True,
                    prompt_count=0,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(target_user)
                db.commit()
                db.refresh(target_user)
                logger.info(f"Pre-created user record for '{clean_email}' (ID: {new_user_id}).")
        elif user_id:
            target_user = db.query(User).filter(User.id == user_id.strip()).first()
            if not target_user:
                raise ValueError(f"User with ID '{user_id}' not found.")
        else:
            raise ValueError("Must provide either --user-email or --user-id to reassign document.")

        doc.user_id = target_user.id
        db.commit()
        logger.info(f"Successfully reassigned document '{doc.title}' ({doc.id}) to {target_user.email} (ID: {target_user.id})!")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Import externally generated Docling chunks & embeddings into Construction RAG PostgreSQL database."
    )
    # Mode switch
    parser.add_argument(
        "--reassign-doc",
        type=str,
        default=None,
        help="Reassign an existing document (by UUID or title) to a user without re-importing.",
    )
    parser.add_argument(
        "--json-file",
        type=Path,
        default=None,
        help="Path to book_export.json or book_export.json.gz generated by Kaggle/Colab.",
    )
    parser.add_argument(
        "--pdf-file",
        type=Path,
        default=None,
        help="Path to the original PDF file to be stored on the server.",
    )
    parser.add_argument(
        "--user-email",
        type=str,
        default=None,
        help="Google account email of the client who should own this document (will be pre-created if not logged in yet).",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        help="Direct user ID (from Better Auth 'user' table) if known.",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="Display title for the document.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch size for database inserts (default: 500).",
    )

    args = parser.parse_args()

    if args.reassign_doc:
        reassign_document(
            doc_identifier=args.reassign_doc,
            user_email=args.user_email,
            user_id=args.user_id,
        )
        return

    if not args.json_file or not args.pdf_file:
        parser.error("--json-file and --pdf-file are required when importing a document.")

    import_document(
        json_path=args.json_file,
        pdf_path=args.pdf_file,
        user_email=args.user_email,
        user_id=args.user_id,
        custom_title=args.title,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
