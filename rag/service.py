"""
rag/service.py
==============
RAG service — the single entry point used by the FastAPI layer (and, later,
the Agentic AI layer) to interact with the maintenance knowledge base.

Public API
----------
``RAGService.ingest()``   — load documents, embed, and persist to ChromaDB.
``RAGService.query()``    — retrieve the top-k chunks relevant to a question.

The service is a plain class (not a singleton) so it can be easily injected
and mocked in tests.  A module-level factory function is provided for the
FastAPI dependency-injection pattern.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from backend.core.config import get_settings
from rag.embedder import KNOWLEDGE_BASE_DIR, ingest
from rag.retriever import RetrievalResult, retrieve

logger = logging.getLogger(__name__)


class RAGService:
    """
    Facade over the embedder and retriever modules.

    Parameters
    ----------
    persist_dir:
        ChromaDB persistence directory (from ``settings.CHROMA_PERSIST_DIR``).
    embedding_model:
        Sentence-transformers model name (from ``settings.EMBEDDING_MODEL``).
    knowledge_base_dir:
        Root of the markdown knowledge base (defaults to the project-level
        ``knowledge_base/`` directory next to the repository root).
    """

    def __init__(
        self,
        persist_dir: str,
        embedding_model: str,
        knowledge_base_dir: Path = KNOWLEDGE_BASE_DIR,
    ) -> None:
        self._persist_dir = persist_dir
        self._embedding_model = embedding_model
        self._knowledge_base_dir = knowledge_base_dir
        self._ingested = False

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def ingest(self) -> int:
        """
        (Re-)build the vector store from the knowledge base.

        Safe to call multiple times; the collection is replaced on each run.

        Returns
        -------
        int
            Number of chunks indexed.
        """
        count = ingest(
            persist_dir=self._persist_dir,
            embedding_model=self._embedding_model,
            knowledge_base_dir=self._knowledge_base_dir,
        )
        self._ingested = count > 0
        logger.info("RAGService: ingest complete — %d chunk(s) indexed.", count)
        return count

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(self, question: str, top_k: int = 4) -> list[RetrievalResult]:
        """
        Return the top-k maintenance knowledge chunks relevant to *question*.

        Parameters
        ----------
        question:
            Free-text maintenance or troubleshooting question.
        top_k:
            Maximum number of results to return (1–10).

        Returns
        -------
        list[RetrievalResult]
            Ranked retrieval results.  Empty if the knowledge base has not
            been ingested yet or the query matches nothing.
        """
        top_k = max(1, min(top_k, 10))
        if not self._ingested:
            logger.warning(
                "RAGService.query() called before ingest(). "
                "Results may be empty if the collection has not been built."
            )
        return retrieve(
            query=question,
            persist_dir=self._persist_dir,
            embedding_model=self._embedding_model,
            top_k=top_k,
        )

    @property
    def is_ready(self) -> bool:
        """True after a successful ingest, False otherwise."""
        return self._ingested


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    """
    Return a cached :class:`RAGService` instance.

    Use as a FastAPI dependency::

        @router.get("/rag/query")
        def query_kb(svc: RAGService = Depends(get_rag_service)):
            ...
    """
    s = get_settings()
    return RAGService(
        persist_dir=s.CHROMA_PERSIST_DIR,
        embedding_model=s.EMBEDDING_MODEL,
    )
