# Large Document Ingestion Workflow (2,000+ Pages)

This directory contains the tools to ingest massive PDF documents (such as 2,400+ page building codes, specification manuals, or books) completely within the **Free Tier** without risking Out-Of-Memory (OOM) crashes on your production VPS.

---

## Architecture Overview

```
1. 2400-Page PDF (57 MB)
      ↓
2. Process on Kaggle / Google Colab (Free 30GB RAM + Free T4 GPU)
   - Windowed Docling extraction (TableFormer, bounding boxes, markdown)
   - GPU-accelerated Embeddings:
     * BAAI/bge-base-en-v1.5 (Local SentenceTransformer on GPU, ~2 mins, 100% free)
     * OR Gemini Embeddings (gemini-embedding-001, 768-dim, API throttled)
   - Generates 'book_export.json.gz' (~15 MB)
      ↓
3. Transfer 'book_export.json.gz' + original PDF to VPS via scp/curl
      ↓
4. Run on VPS:
   python -m backend.scripts.import_external_doc \
       --json-file book_export.json.gz \
       --pdf-file client_book.pdf \
       --user-email client@example.com
      ↓
5. Seamlessly available in the Web UI:
   - pgvector hybrid retrieval
   - Citation highlighting & page navigation in PdfProofViewer
```

---

## Step 1: Run Ingestion on Kaggle or Google Colab

1. **Create a new Kaggle Notebook** (or Colab notebook) and enable **GPU** (e.g. T4 or P100).
2. **Upload your PDF** to the notebook working directory (or attach as a Kaggle dataset).
3. In a cell, install the dependencies:
   ```bash
   !pip install -q docling docling-core sentence-transformers pypdf tqdm
   ```
4. Copy the contents of [`kaggle_ingest_book.py`](file:///d:/codes/construction-rag-2/backend/scripts/kaggle_ingest_book.py) into a notebook cell.
5. Set your parameters:
   ```python
   PDF_INPUT_PATH = "your_actual_book_name.pdf"
   
   # For BAAI/bge-base-en-v1.5 (Recommended - No API key needed, superfast on GPU):
   EMBEDDING_PROVIDER = "local"
   EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
   EMBEDDING_DIMENSION = 768
   ```
6. Run the cell.
   - It will process in windows of 50 pages, preventing memory leaks.
   - It extracts tables and bounding boxes identical to the production Docling service.
   - It encodes all chunks into 768-dimensional unit-normalized vectors directly on the Kaggle GPU in ~2 minutes.
   - Progress is automatically checkpointed to `ingestion_checkpoint.json` in case of interruptions.
7. Download the resulting **`book_export.json.gz`** file.

---

## Step 2: Transfer to Your Production Server

Use `scp` or `rsync` from your local terminal:
```bash
# Transfer the export file
scp book_export.json.gz root@your-server-ip:/root/

# Transfer the original PDF file
scp your_actual_book_name.pdf root@your-server-ip:/root/
```

---

## Step 3: Import into PostgreSQL & Production Server

SSH into your production server and run:

```bash
# If running inside Docker container:
docker exec -it construction-rag-backend python -m backend.scripts.import_external_doc \
    --json-file /root/book_export.json.gz \
    --pdf-file /root/your_actual_book_name.pdf \
    --user-email "client@example.com" \
    --title "Client Comprehensive Building Manual"

# Or if running directly in the Python virtualenv on host:
python -m backend.scripts.import_external_doc \
    --json-file /root/book_export.json.gz \
    --pdf-file /root/your_actual_book_name.pdf \
    --user-email "client@example.com" \
    --title "Client Comprehensive Building Manual"
```

### What this does automatically:
1. **User Association (Even Before First Login)**:
   - If the client's email is provided (e.g. `--user-email "client@gmail.com"`), the script checks if the user exists.
   - If they **haven't logged in yet**, it automatically **pre-creates** their user record in the Better Auth `"user"` table.
   - When the client later signs in via **Google OAuth** using that email, Better Auth automatically links their Google session to this existing account, and the book will already be waiting in their sidebar!
2. **Copies the PDF**: Moves the file to `data/uploads/<document_id>.pdf` so the frontend PDF viewer can stream it.
3. **Database Insertion**: Inserts the `Document` record with `status='indexed'` and bulk-inserts all chunks with 768-dim `Vector` embeddings.
4. **Optimizes Index**: Runs `VACUUM ANALYZE` so pgvector indexes and queries perform immediately.

---

## Alternative: Reassigning Ownership Anytime

If you imported the document first without knowing their email, you can assign or reassign it to them at any time with a single command:

```bash
python -m backend.scripts.import_external_doc \
    --reassign-doc "Client Comprehensive Building Manual" \
    --user-email "client@gmail.com"
```

---

## Verification

1. When the client logs into the web app with their Google account (`client@gmail.com`), the document appears immediately in their sidebar under **Documents**.
2. They can chat, ask questions, and click citations to highlight proof bounding boxes on the target pages.
3. Ask questions about the book in the chat:
   - Citations will correctly reference exact page numbers.
   - Clicking a citation opens the PDF viewer at the target page with bounding box proof highlights.
