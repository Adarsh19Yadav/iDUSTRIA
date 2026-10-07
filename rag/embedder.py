"""
rag/embedder.py
===============
Document loading and ChromaDB ingestion for the maintenance knowledge base.

Responsibilities
----------------
- Walk ``knowledge_base/`` and load every ``.md`` file.
- Split each document into fixed-size chunks with a small overlap.
- Embed chunks with ``sentence-transformers`` (local, no API key required).
- Persist the vector store to the ChromaDB directory defined in settings.

Design decisions
----------------
- Plain ``chromadb`` client (no LangChain wrappers) — minimal dependencies.
- ``sentence-transformers`` runs entirely locally — no external API calls.
- Chunks are stored with metadata: ``source`` (file path), ``chunk_index``.
- Re-ingest is idempotent: the collection is cleared and rebuilt on each call.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent / "knowledge_base"
_DEFAULT_CHUNK_SIZE = 500          # characters
_DEFAULT_CHUNK_OVERLAP = 80        # characters
COLLECTION_NAME = "maintenance_kb"


@dataclass
class Document:
    """A single text chunk ready for embedding."""

    content: str
    source: str          # relative path from the knowledge_base root
    chunk_index: int = 0
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Document loading
# ---------------------------------------------------------------------------

def load_documents(knowledge_base_dir: Path = KNOWLEDGE_BASE_DIR) -> list[Document]:
    """
    Recursively load all ``.md`` files under *knowledge_base_dir*.

    Returns a flat list of :class:`Document` objects — one per file before chunking.
    """
    docs: list[Document] = []
    if not knowledge_base_dir.exists():
        logger.warning("Knowledge base directory not found: %s", knowledge_base_dir)
        return docs

    for md_file in sorted(knowledge_base_dir.rglob("*.md")):
        relative = md_file.relative_to(knowledge_base_dir).as_posix()
        try:
            content = md_file.read_text(encoding="utf-8").strip()
            if content:
                docs.append(Document(content=content, source=relative))
                logger.debug("Loaded document: %s (%d chars)", relative, len(content))
        except OSError as exc:
            logger.error("Failed to read %s: %s", md_file, exc)

    logger.info("Loaded %d document(s) from %s", len(docs), knowledge_base_dir)
    return docs


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_document(
    doc: Document,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    overlap: int = _DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    """
    Split a document into overlapping character-level chunks.

    Chunks are split on paragraph / sentence boundaries where possible to
    avoid cutting in the middle of a sentence, then fall back to hard splits.
    """
    text = doc.content
    if len(text) <= chunk_size:
        return [Document(content=text, source=doc.source, chunk_index=0)]

    # Split on paragraph boundaries first, then recombine up to chunk_size.
    paragraphs = re.split(r"\n{2,}", text)
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        candidate = (current + "\n\n" + para).strip() if current else para
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # If the single paragraph itself is larger than chunk_size,
            # hard-split it.
            if len(para) > chunk_size:
                start = 0
                while start < len(para):
                    end = start + chunk_size
                    chunks.append(para[start:end])
                    start = end - overlap
            else:
                current = para

    if current:
        chunks.append(current)

    return [
        Document(content=chunk, source=doc.source, chunk_index=i)
        for i, chunk in enumerate(chunks)
    ]


def chunk_documents(
    docs: Sequence[Document],
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    overlap: int = _DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    """Chunk all documents and return a flat list."""
    result: list[Document] = []
    for doc in docs:
        result.extend(chunk_document(doc, chunk_size=chunk_size, overlap=overlap))
    logger.info("Produced %d chunk(s) from %d document(s)", len(result), len(docs))
    return result


# ---------------------------------------------------------------------------
# ChromaDB ingestion
# ---------------------------------------------------------------------------

def _make_chroma_client(persist_dir: str):
    """Return a persistent ChromaDB client, importing lazily."""
    import chromadb  # noqa: PLC0415

    return chromadb.PersistentClient(path=persist_dir)


def _make_embedding_function(model_name: str):
    """Return a ChromaDB-compatible embedding function backed by sentence-transformers."""
    from chromadb.utils.embedding_functions import (  # noqa: PLC0415
        SentenceTransformerEmbeddingFunction,
    )

    return SentenceTransformerEmbeddingFunction(model_name=model_name)


def ingest(
    persist_dir: str,
    embedding_model: str,
    knowledge_base_dir: Path = KNOWLEDGE_BASE_DIR,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = _DEFAULT_CHUNK_OVERLAP,
) -> int:
    """
    Load, chunk, embed, and persist the knowledge base.

    The collection is **replaced** on each call (idempotent re-ingest).

    Parameters
    ----------
    persist_dir:
        Path where ChromaDB persists its data (from ``settings.CHROMA_PERSIST_DIR``).
    embedding_model:
        Sentence-transformers model name (from ``settings.EMBEDDING_MODEL``).
    knowledge_base_dir:
        Root of the markdown knowledge base.
    chunk_size:
        Target character count per chunk.
    chunk_overlap:
        Character overlap between adjacent chunks.

    Returns
    -------
    int
        Number of chunks ingested.
    """
    os.makedirs(persist_dir, exist_ok=True)

    raw_docs = load_documents(knowledge_base_dir)
    if not raw_docs:
        logger.warning("No documents found — knowledge base is empty.")
        return 0

    chunks = chunk_documents(raw_docs, chunk_size=chunk_size, overlap=chunk_overlap)

    client = _make_chroma_client(persist_dir)
    embedding_fn = _make_embedding_function(embedding_model)

    # Delete and recreate the collection for idempotent re-ingest.
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.debug("Deleted existing collection '%s'.", COLLECTION_NAME)
    except Exception:  # collection may not exist on first run
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    ids = [f"{c.source}::chunk{c.chunk_index}" for c in chunks]
    documents = [c.content for c in chunks]
    metadatas = [{"source": c.source, "chunk_index": c.chunk_index} for c in chunks]

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    logger.info(
        "Ingested %d chunk(s) into collection '%s' at '%s'.",
        len(chunks),
        COLLECTION_NAME,
        persist_dir,
    )
    return len(chunks)
