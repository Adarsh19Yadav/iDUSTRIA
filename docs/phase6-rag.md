# Phase 6 — Maintenance RAG (Retrieval-Augmented Generation)

## Overview

Phase 6 introduces a knowledge-base retrieval system built on ChromaDB and sentence-transformers.
The RAG pipeline enables the Agentic AI (Phase 7) to ground its recommendations in curated
maintenance documentation, rather than relying solely on model predictions.

## Architecture

```
knowledge_base/         (markdown source documents)
        │
        ▼
RAGService.ingest()     (chunk + embed → ChromaDB)
        │
        ▼
ChromaDB                (persistent vector store)
        │
        ▼
RAGService.query()      (semantic similarity search)
        │
        ▼
RetrievalResult[]       (content, source, chunk_index, distance)
```

## Components

| Module | Purpose |
|---|---|
| `rag/service.py` | `RAGService` — ingest, query, readiness check |
| `rag/retriever.py` | Low-level ChromaDB retrieval; `RetrievalResult` dataclass |
| `rag/chunker.py` | Markdown-aware document chunking |
| `rag/embedder.py` | sentence-transformers embedding wrapper |
| `knowledge_base/` | Source maintenance guidance documents (Markdown) |
| `backend/api/rag.py` | FastAPI router exposing RAG endpoints |

## API Endpoints

### `POST /api/v1/rag/query`

Query the knowledge base with a natural-language maintenance question.

**Public** — no API key required.

```json
{
  "question": "What are the signs of bearing spalling?",
  "top_k": 4
}
```

**Response:** top-k most relevant chunks with content, source, and cosine distance.

### `POST /api/v1/rag/ingest`

(Re-)ingest the knowledge base. Embeds all markdown documents and indexes them in ChromaDB.

**Protected** — requires `X-API-Key` header.

Automatically triggered at application startup via the `lifespan` handler in `backend/main.py`.

### `GET /api/v1/rag/status`

Returns whether the knowledge base has been ingested and is ready to query.

**Public** — no API key required.

## Knowledge Base

The knowledge base consists of markdown documents in `knowledge_base/`. Documents are:

1. Chunked by the `RAGService` on ingest
2. Embedded using `sentence-transformers/all-MiniLM-L6-v2`
3. Indexed in ChromaDB at `CHROMA_PERSIST_DIR` (default: `./backend/chroma_db`)

## Configuration

| Variable | Default | Description |
|---|---|---|
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace embedding model |
| `CHROMA_PERSIST_DIR` | `./backend/chroma_db` | ChromaDB persistence directory |

## Security

- The `rag/ingest` endpoint is protected by the API key to prevent unauthorized knowledge-base modification.
- The `rag/query` endpoint is public to support the dashboard and agent without friction.
- Document content is sanitized through Pydantic schema validation before returning to callers.
- No user input is written to the knowledge base.

## Limitations

- Knowledge base content is static and curated. It does not learn from user interactions.
- Retrieval is semantic similarity search — it does not guarantee factual correctness of retrieved content.
- The quality of RAG responses depends on the quality and coverage of the source documents.
- Embeddings are computed locally using sentence-transformers; no data is sent to external embedding APIs.
