# 🔍 Search in PDF, Semantically, with Proof

> Not "Chat with PDF" — **Search with Proof.**

A citation-aware RAG pipeline that handles diverse PDF content (text, tables, images, diagrams, multi-column, LaTeX, scanned documents) and returns answers with **exact page numbers, bounding boxes, and section hierarchy** as proof.

## Features

- 📄 **Docling** — intelligent PDF extraction (layout analysis, OCR, table detection, figure extraction)
- ✂️ **HybridChunker** — structure-aware chunking with full citation provenance
- 🖼️ **Multimodal VLM** — generates text summaries from images/figures
- 🔀 **Hybrid Search** — BM25 (keyword) + Vector (semantic) with Reciprocal Rank Fusion
- 📌 **Citations** — every answer traces back to exact page + bounding box coordinates
- 🔌 **Provider-agnostic** — switch between Ollama, Gemini, OpenRouter, OpenAI via `.env`
- 🐳 **Dockerized** — one command to start everything

## Quick Start

### With Docker (recommended)

```bash
# 1. Configure
cp .env.example .env
# Edit .env with your preferred LLM provider

# 2. Start all services
docker-compose up --build

# 3. Pull Ollama models (if using local LLM)
docker exec -it construction-rag-2-ollama-1 ollama pull llama3.2
docker exec -it construction-rag-2-ollama-1 ollama pull llava

# 4. Open the notebook
# → http://localhost:8888/notebooks/rag_pipeline.ipynb
```

### Without Docker

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env — set OLLAMA_BASE_URL=http://localhost:11434

# 3. Start Ollama (if using local LLM)
ollama pull llama3.2
ollama pull llava

# 4. Run the notebook
jupyter notebook notebooks/rag_pipeline.ipynb
```

## Switching LLM Providers

Edit `.env` — **zero code changes** needed:

| Provider | `.env` Config |
|----------|--------------|
| **Ollama** (local) | `LLM_PROVIDER=ollama` `LLM_MODEL=llama3.2` |
| **Google Gemini** | `LLM_PROVIDER=gemini` `LLM_MODEL=gemini-2.0-flash` `GOOGLE_API_KEY=...` |
| **OpenRouter** | `LLM_PROVIDER=openrouter` `LLM_MODEL=meta-llama/llama-3.1-70b-instruct` `OPENROUTER_API_KEY=...` |
| **OpenAI** | `LLM_PROVIDER=openai` `LLM_MODEL=gpt-4o-mini` `OPENAI_API_KEY=...` |

You can mix providers (e.g., local embeddings + Gemini for generation + OpenAI for vision).

## Project Structure

```
├── .env.example          # Config template
├── Dockerfile            # Jupyter + Docling environment
├── docker-compose.yml    # Jupyter + ChromaDB + Ollama
├── requirements.txt      # Python dependencies
├── config/
│   └── settings.py       # Loads .env, typed config
├── providers/
│   ├── factory.py        # get_llm(), get_vlm(), get_embeddings()
│   ├── ollama_provider.py
│   ├── gemini_provider.py
│   ├── openrouter_provider.py
│   └── openai_provider.py
├── notebooks/
│   └── rag_pipeline.ipynb  # Main RAG notebook (12 cells)
├── pdfs/                 # Drop your PDFs here
└── data/                 # Persistent stores
    ├── chroma/           # Vector DB
    └── docstore/         # Citation metadata
```

## Architecture

### Ingestion: PDF → Chunks with Citations
`PDF` → `Docling (layout + OCR + tables)` → `HybridChunker` → `Chunks with (page, bbox, heading, type)` → `ChromaDB + BM25`

### Retrieval: Query → Answer with Proof
`Query` → `BM25 + Vector` → `RRF Fusion` → `Top-K with citations` → `LLM (citation-forced prompt)` → `Answer + [Source N] citations`

## License

MIT
