"""
rag/retriever.py
================
Semantic retrieval from the ChromaDB maintenance knowledge base.

Responsibilities
----------------
- Open the persisted ChromaDB collection.
- Accept a natural-language query and return the top-k most relevant chunks.
- Return structured :class:`RetrievalResult` objects — no raw dicts leaked.

Design decisions
----------------
- Stateless helper function interface for ease of testing and use from the service layer.
- Cosine similarity search (configured at ingest time on the collection).
- Returns an empty list gracefully when the collection does not exist.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_DEFAULT_TOP_K = 4


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RetrievalResult:
    """A single retrieved chunk with its relevance distance."""

    content: str
    source: str
    chunk_index: int
    distance: float            # lower = more similar (cosine distance ∈ [0, 2])
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def retrieve(
    query: str,
    persist_dir: str,
    embedding_model: str,
    collection_name: str = "maintenance_kb",
    top_k: int = _DEFAULT_TOP_K,
) -> list[RetrievalResult]:
    """
    Query the ChromaDB collection and return the *top_k* closest chunks.

    Parameters
    ----------
    query:
        Natural-language maintenance question.
    persist_dir:
        Path to the ChromaDB persistence directory.
    embedding_model:
        Sentence-transformers model name — must match what was used at ingest time.
    collection_name:
        ChromaDB collection to search.
    top_k:
        Number of results to return.

    Returns
    -------
    list[RetrievalResult]
        Ranked list of results (closest first). Empty if the collection is missing.
    """
    if not query or not query.strip():
        logger.warning("Empty query passed to retrieve(); returning no results.")
        return []

    try:
        import chromadb  # noqa: PLC0415
        from chromadb.utils.embedding_functions import (  # noqa: PLC0415
            SentenceTransformerEmbeddingFunction,
        )
    except ImportError as exc:
        logger.error("chromadb is not installed: %s", exc)
        return []

    embedding_fn = SentenceTransformerEmbeddingFunction(model_name=embedding_model)
    client = chromadb.PersistentClient(path=persist_dir)

    try:
        collection = client.get_collection(
            name=collection_name,
            embedding_function=embedding_fn,
        )
    except Exception as exc:
        logger.warning(
            "Collection '%s' not found in '%s': %s — has ingest() been run?",
            collection_name,
            persist_dir,
            exc,
        )
        return []

    response = collection.query(
        query_texts=[query.strip()],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    results: list[RetrievalResult] = []
    for doc, meta, dist in zip(
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0],
    ):
        results.append(
            RetrievalResult(
                content=doc,
                source=meta.get("source", ""),
                chunk_index=int(meta.get("chunk_index", 0)),
                distance=float(dist),
                metadata=dict(meta),
            )
        )

    logger.debug(
        "Query '%s...' returned %d result(s).", query[:60], len(results)
    )
    return results
