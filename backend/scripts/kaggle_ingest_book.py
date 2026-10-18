"""
Self-contained Kaggle / Google Colab script for heavy, large-scale PDF ingestion.
Designed for 2,000+ page documents with complex tables and structure.

Features:
- Page-windowed Docling extraction (e.g. 50-100 pages/batch) to prevent memory fragmentation.
- Full TableFormer table structure recognition & bounding box extraction matching frontend citations.
- GPU-accelerated local embedding generation using BAAI/bge-base-en-v1.5 (or Google Gemini Free Tier).
- Exports a compact 'book_export.json.gz' ready for direct import into PostgreSQL + pgvector.

Requirements on Kaggle / Colab (GPU accelerated):
    !pip install -q docling docling-core sentence-transformers pypdf tqdm
    # Optional if using Gemini provider instead: !pip install -q langchain-google-genai
"""

import os
import gc
import sys
import time
import json
import gzip
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from pypdf import PdfReader, PdfWriter
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("kaggle_ingest")

# ==============================================================================
# CONFIGURATION
# ==============================================================================
PDF_INPUT_PATH = "client_large_book.pdf"       # Name of your uploaded PDF file in Kaggle
OUTPUT_EXPORT_FILE = "book_export.json.gz"      # Output file to download and send to server
CHECKPOINT_FILE = "ingestion_checkpoint.json"   # Intermediate recovery file

# Embedding Provider:
# - "local": Uses BAAI/bge-base-en-v1.5 via sentence-transformers on GPU (fastest & 100% free)
# - "gemini": Uses Google Gemini embeddings API (gemini-embedding-001)
EMBEDDING_PROVIDER = "local"
EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
EMBEDDING_DIMENSION = 768

# Only required if EMBEDDING_PROVIDER == "gemini"
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY", "YOUR_GEMINI_API_KEY_HERE")

WINDOW_PAGE_SIZE = 50       # Number of pages to process with Docling per window (prevents OOM)
CHUNK_MAX_TOKENS = 512      # Maximum tokens per chunk
CHUNK_MERGE_PEERS = True

# Batch processing
LOCAL_EMBED_BATCH_SIZE = 64 # Batch size on GPU for SentenceTransformer
GEMINI_EMBED_BATCH_SIZE = 50 # Chunks per Gemini API call
GEMINI_API_CALL_DELAY_SEC = 2.0
# ==============================================================================


def check_environment():
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"GPU Detected: {torch.cuda.get_device_name(0)} (VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB)")
        else:
            logger.warning("No GPU detected. Running on CPU (Docling TableFormer will be slower).")
    except Exception:
        pass


def slice_pdf_pages(input_pdf: Path, start_page: int, end_page: int, temp_output: Path):
    """Extracts a sub-range of pages [start_page, end_page] (1-indexed) into a temporary PDF."""
    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()
    
    # 0-indexed slicing
    for page_idx in range(start_page - 1, min(end_page, len(reader.pages))):
        writer.add_page(reader.pages[page_idx])
        
    with open(temp_output, "wb") as f:
        writer.write(f)


def extract_window_chunks(
    temp_pdf: Path, 
    page_offset: int, 
    max_tokens: int = 512
) -> List[Dict[str, Any]]:
    """Runs Docling and HybridChunker on a sub-range of pages, adjusting page numbers by offset."""
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.datamodel.base_models import InputFormat
    from docling.chunking import HybridChunker

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.mode = TableFormerMode.FAST
    pipeline_options.do_ocr = False  # Set to True only if your PDF is scanned without digital text
    pipeline_options.generate_picture_images = False

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    result = converter.convert(str(temp_pdf))
    doc = result.document

    chunker = HybridChunker(max_tokens=max_tokens, merge_peers=CHUNK_MERGE_PEERS)
    raw_chunks = list(chunker.chunk(doc))

    window_chunks = []
    for chunk in raw_chunks:
        page_numbers = []
        bboxes = []
        element_types = set()

        if hasattr(chunk, 'meta') and hasattr(chunk.meta, 'doc_items'):
            for item in chunk.meta.doc_items:
                if hasattr(item, 'label'):
                    element_types.add(str(item.label))
                if hasattr(item, 'prov'):
                    for prov in item.prov:
                        if hasattr(prov, 'page_no'):
                            # CRITICAL: Offset local sub-PDF page number to match true book page
                            actual_page = prov.page_no + page_offset
                            page_numbers.append(actual_page)

                        if hasattr(prov, 'bbox') and prov.bbox:
                            page_w, page_h = None, None
                            if hasattr(doc, 'pages') and doc.pages and hasattr(prov, 'page_no'):
                                page_obj = None
                                if isinstance(doc.pages, dict):
                                    page_obj = doc.pages.get(prov.page_no) or doc.pages.get(str(prov.page_no))
                                elif isinstance(doc.pages, list) and 0 <= prov.page_no - 1 < len(doc.pages):
                                    page_obj = doc.pages[prov.page_no - 1]
                                
                                if page_obj and hasattr(page_obj, 'size') and page_obj.size:
                                    page_w = float(page_obj.size.width)
                                    page_h = float(page_obj.size.height)

                            try:
                                if hasattr(prov.bbox, 'to_top_left_origin') and page_h:
                                    tl_bbox = prov.bbox.to_top_left_origin(page_h)
                                    l, t, r, b = float(tl_bbox.l), float(tl_bbox.t), float(tl_bbox.r), float(tl_bbox.b)
                                else:
                                    l, t, r, b = float(prov.bbox.l), float(prov.bbox.t), float(prov.bbox.r), float(prov.bbox.b)
                            except Exception:
                                l, t, r, b = float(prov.bbox.l), float(prov.bbox.t), float(prov.bbox.r), float(prov.bbox.b)

                            bboxes.append({
                                "l": round(l, 2),
                                "t": round(t, 2),
                                "r": round(r, 2),
                                "b": round(b, 2),
                                "coord_origin": "TOPLEFT",
                                "page_width": page_w,
                                "page_height": page_h,
                            })

        headings = []
        if hasattr(chunk, 'meta') and hasattr(chunk.meta, 'headings') and chunk.meta.headings:
            headings = [str(h) for h in chunk.meta.headings]

        element_type = "table" if "table" in element_types else "text"

        text_content = chunk.text if hasattr(chunk, 'text') else str(chunk)
        if text_content.strip():
            window_chunks.append({
                "text": text_content,
                "page_numbers": sorted(set(page_numbers)),
                "bboxes": bboxes,
                "headings": headings,
                "element_type": element_type,
            })

    # Cleanup memory
    del converter, doc, result, chunker, raw_chunks
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass

    return window_chunks


def run_windowed_extraction(pdf_path: Path) -> List[Dict[str, Any]]:
    """Loops through all pages in windows of WINDOW_PAGE_SIZE and accumulates chunks."""
    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    logger.info(f"Total PDF pages to process: {total_pages}")

    # Check for existing checkpoint
    all_chunks = []
    start_window_page = 1
    if Path(CHECKPOINT_FILE).exists():
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                checkpoint_data = json.load(f)
                all_chunks = checkpoint_data.get("chunks", [])
                start_window_page = checkpoint_data.get("next_page", 1)
                logger.info(f"Resuming from checkpoint at page {start_window_page} with {len(all_chunks)} existing chunks.")
        except Exception as e:
            logger.warning(f"Could not load checkpoint: {e}")

    temp_slice_file = Path("temp_slice.pdf")

    for current_start in range(start_window_page, total_pages + 1, WINDOW_PAGE_SIZE):
        current_end = min(current_start + WINDOW_PAGE_SIZE - 1, total_pages)
        logger.info(f"Processing page window: {current_start} - {current_end} (of {total_pages})...")

        slice_pdf_pages(pdf_path, current_start, current_end, temp_slice_file)
        
        # page_offset = current_start - 1 so that local page 1 becomes actual page current_start
        window_chunks = extract_window_chunks(temp_slice_file, page_offset=current_start - 1, max_tokens=CHUNK_MAX_TOKENS)
        all_chunks.extend(window_chunks)

        if temp_slice_file.exists():
            temp_slice_file.unlink()

        # Save extraction checkpoint
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump({"next_page": current_end + 1, "chunks": all_chunks}, f)

        logger.info(f"Progress: Window {current_start}-{current_end} done. Accumulated chunks: {len(all_chunks)}")

    # Assign global chunk_index
    for idx, c in enumerate(all_chunks):
        c["chunk_index"] = idx

    logger.info(f"Extraction complete! Total chunks extracted: {len(all_chunks)}")
    return all_chunks


def _embed_single_with_retry(model, text: str, max_retries: int = 5) -> Optional[List[float]]:
    """Embeds a single text with retries and exponential backoff."""
    clean_text = text.strip()
    if not clean_text:
        clean_text = "[Empty Section]"
    # Guard against excessively large text exceeding embedding context
    if len(clean_text) > 10000:
        clean_text = clean_text[:10000]

    backoff = 5.0
    for attempt in range(max_retries):
        try:
            return model.embed_query(clean_text)
        except Exception as e:
            err_str = str(e).lower()
            logger.warning(f"Single embed failed (attempt {attempt+1}/{max_retries}): {e}")
            if "429" in err_str or "quota" in err_str or "resource" in err_str:
                time.sleep(backoff)
                backoff *= 2.0
            else:
                time.sleep(3.0)
    return None


def generate_local_embeddings(chunks: List[Dict[str, Any]], model_name: str = EMBEDDING_MODEL, batch_size: int = LOCAL_EMBED_BATCH_SIZE):
    """Generates embeddings using sentence-transformers (GPU accelerated with BAAI/bge-base-en-v1.5)."""
    import torch
    from sentence_transformers import SentenceTransformer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Loading local embedding model '{model_name}' on device: {device}...")
    model = SentenceTransformer(model_name, device=device)

    total_chunks = len(chunks)
    logger.info(f"Generating local embeddings for {total_chunks} chunks using model '{model_name}' ({EMBEDDING_DIMENSION} dims)...")

    # Find where to resume (chunks that already have embeddings)
    already_embedded = sum(1 for c in chunks if c.get("embedding") is not None and len(c["embedding"]) == EMBEDDING_DIMENSION)
    if already_embedded > 0:
        logger.info(f"Resuming embedding process: {already_embedded} / {total_chunks} already completed.")

    for start_idx in tqdm(range(already_embedded, total_chunks, batch_size), desc="Local Embedding Batches"):
        end_idx = min(start_idx + batch_size, total_chunks)
        batch_chunks = chunks[start_idx:end_idx]

        # Sanitize texts (BGE models embed raw chunk texts directly)
        texts = []
        for c in batch_chunks:
            txt = c.get("text", "").strip()
            if not txt:
                txt = "[Empty Section]"
            texts.append(txt)

        # Batch encode with unit normalization (matching pgvector cosine distance)
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True
        )

        for i, vec in enumerate(vectors):
            batch_chunks[i]["embedding"] = vec.tolist()

        # Save checkpoint periodically so progress is never lost
        if (start_idx // batch_size) % 10 == 0 or end_idx >= total_chunks:
            with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                json.dump({"next_page": 999999, "chunks": chunks}, f)

    logger.info("All local embeddings generated successfully!")


def generate_gemini_embeddings(chunks: List[Dict[str, Any]], api_key: str):
    """Generates embeddings using Gemini Free Tier with rate limiting, sanitization, and fallback."""
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    embeddings_model = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=api_key,
        output_dimensionality=EMBEDDING_DIMENSION,
    )

    total_chunks = len(chunks)
    logger.info(f"Generating embeddings for {total_chunks} chunks using model '{EMBEDDING_MODEL}' ({EMBEDDING_DIMENSION} dims)...")

    # Find where to resume (chunks that already have embeddings)
    already_embedded = sum(1 for c in chunks if c.get("embedding") is not None and len(c["embedding"]) == EMBEDDING_DIMENSION)
    logger.info(f"Resuming embedding process: {already_embedded} / {total_chunks} already completed.")

    for start_idx in tqdm(range(already_embedded, total_chunks, GEMINI_EMBED_BATCH_SIZE), desc="Gemini Embedding Batches"):
        end_idx = min(start_idx + GEMINI_EMBED_BATCH_SIZE, total_chunks)
        batch_chunks = chunks[start_idx:end_idx]
        
        # Sanitize texts
        texts = []
        for c in batch_chunks:
            txt = c.get("text", "").strip()
            if not txt:
                txt = "[Empty Section]"
            if len(txt) > 10000:
                txt = txt[:10000]
            texts.append(txt)

        # Attempt batch embedding
        batch_success = False
        backoff = 5.0
        max_batch_retries = 3

        for attempt in range(max_batch_retries):
            try:
                vectors = embeddings_model.embed_documents(texts)
                for i, vec in enumerate(vectors):
                    batch_chunks[i]["embedding"] = vec
                batch_success = True
                break
            except Exception as e:
                err_str = str(e).lower()
                logger.warning(f"Batch {start_idx}-{end_idx} failed (attempt {attempt + 1}/{max_batch_retries}): {e}")
                if "429" in err_str or "quota" in err_str or "resource" in err_str:
                    logger.info(f"Rate limit / quota hit. Waiting {backoff:.1f}s before retrying...")
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    time.sleep(4.0)

        # Fallback: If the batch failed, process items individually to isolate problematic chunks
        if not batch_success:
            logger.info(f"Batch {start_idx}-{end_idx} failed as a group. Switching to item-by-item embedding for this batch...")
            for idx_in_batch, c in enumerate(batch_chunks):
                if c.get("embedding") is not None:
                    continue
                vec = _embed_single_with_retry(embeddings_model, texts[idx_in_batch])
                if vec is not None:
                    c["embedding"] = vec
                else:
                    # Fallback to zero vector if a specific corrupted chunk permanently fails
                    logger.error(f"Chunk {start_idx + idx_in_batch} permanently failed embedding. Using placeholder zero vector.")
                    c["embedding"] = [0.0] * EMBEDDING_DIMENSION
                time.sleep(1.0)

        # Rate limit safety delay
        time.sleep(GEMINI_API_CALL_DELAY_SEC)

        # Save checkpoint every 2 batches so progress is never lost
        if (start_idx // GEMINI_EMBED_BATCH_SIZE) % 2 == 0 or end_idx >= total_chunks:
            with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                json.dump({"next_page": 999999, "chunks": chunks}, f)

    logger.info("All Gemini embeddings generated successfully!")


def main():
    check_environment()
    pdf_path = Path(PDF_INPUT_PATH)
    if not pdf_path.exists():
        print(f"ERROR: Cannot find '{PDF_INPUT_PATH}'. Please upload your PDF or set PDF_INPUT_PATH.")
        sys.exit(1)

    provider = EMBEDDING_PROVIDER.lower()
    if provider == "gemini":
        if not GEMINI_API_KEY or "YOUR_GEMINI_API_KEY" in GEMINI_API_KEY:
            print("ERROR: Please set GEMINI_API_KEY before running when EMBEDDING_PROVIDER='gemini'.")
            sys.exit(1)

    # 1. Extraction (Windowed Docling)
    chunks = run_windowed_extraction(pdf_path)

    # 2. Embeddings (Local BAAI/bge or Gemini)
    if provider == "local":
        generate_local_embeddings(chunks, model_name=EMBEDDING_MODEL, batch_size=LOCAL_EMBED_BATCH_SIZE)
    elif provider == "gemini":
        generate_gemini_embeddings(chunks, GEMINI_API_KEY)
    else:
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: '{EMBEDDING_PROVIDER}'. Use 'local' or 'gemini'.")

    # 3. Export package
    file_size = pdf_path.stat().st_size
    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)

    export_payload = {
        "document": {
            "filename": pdf_path.name,
            "file_size": file_size,
            "title": pdf_path.stem.replace("_", " ").title(),
            "content_type": "mixed",
            "chunk_count": len(chunks),
            "docling_metadata": {
                "page_count": total_pages,
                "chunk_count": len(chunks),
                "generated_by": "kaggle_pipeline",
                "embedding_provider": EMBEDDING_PROVIDER,
                "embedding_model": EMBEDDING_MODEL,
                "embedding_dimension": EMBEDDING_DIMENSION,
            }
        },
        "chunks": chunks
    }

    logger.info(f"Writing compressed export to {OUTPUT_EXPORT_FILE}...")
    with gzip.open(OUTPUT_EXPORT_FILE, "wt", encoding="utf-8") as f:
        json.dump(export_payload, f)

    output_size_mb = Path(OUTPUT_EXPORT_FILE).stat().st_size / (1024 * 1024)
    logger.info(f"Done! Created '{OUTPUT_EXPORT_FILE}' ({output_size_mb:.2f} MB).")
    print("\n" + "=" * 60)
    print(f"EXPORT READY: {OUTPUT_EXPORT_FILE}")
    print(f"Model: {EMBEDDING_MODEL} ({EMBEDDING_DIMENSION}-dim) | Provider: {EMBEDDING_PROVIDER}")
    print(f"Total Pages: {total_pages} | Total Chunks: {len(chunks)} | File: {output_size_mb:.2f} MB")
    print("=" * 60)
    print("NEXT STEPS:")
    print("1. Download 'book_export.json.gz' from Kaggle.")
    print("2. Transfer it and your PDF to your production server.")
    print("3. Run on your server:")
    print(f"   python -m backend.scripts.import_external_doc --json-file {OUTPUT_EXPORT_FILE} --pdf-file {PDF_INPUT_PATH} --user-email client@example.com")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
