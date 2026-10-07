"""
tests/unit/rag/test_retriever.py
=================================
Unit tests for rag/retriever.py.

The ``retrieve`` function uses lazy imports for chromadb and sentence-transformers.
We patch ``sys.modules`` to inject lightweight mocks so the tests run without
any network or model-download requirements.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from rag.retriever import RetrievalResult, retrieve


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chroma_response(docs: list[str], metadatas: list[dict], distances: list[float]):
    """Build the dict structure that chromadb.Collection.query() returns."""
    return {
        "documents": [docs],
        "metadatas": [metadatas],
        "distances": [distances],
    }


def _make_chromadb_mock():
    """
    Return a (chromadb_mock, ef_cls_mock) pair where chromadb_mock can be
    injected into sys.modules so that the lazy imports inside ``retrieve``
    resolve correctly.
    """
    ef_cls = MagicMock(name="SentenceTransformerEmbeddingFunction")

    ef_module = ModuleType("chromadb.utils.embedding_functions")
    ef_module.SentenceTransformerEmbeddingFunction = ef_cls  # type: ignore[attr-defined]

    utils_module = ModuleType("chromadb.utils")
    utils_module.embedding_functions = ef_module  # type: ignore[attr-defined]

    chroma = MagicMock(name="chromadb")
    chroma.utils = utils_module

    return chroma, ef_cls, ef_module, utils_module


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRetrieve:
    def test_returns_results_on_success(self) -> None:
        chroma, ef_cls, ef_module, utils_module = _make_chromadb_mock()

        mock_collection = MagicMock()
        mock_collection.count.return_value = 3
        mock_collection.query.return_value = _make_chroma_response(
            docs=["Inspect bearings every 1000 hours.", "Use correct grease."],
            metadatas=[
                {"source": "maintenance/bearing.md", "chunk_index": 0},
                {"source": "maintenance/bearing.md", "chunk_index": 1},
            ],
            distances=[0.05, 0.15],
        )
        chroma.PersistentClient.return_value.get_collection.return_value = mock_collection

        with _patch_chromadb(chroma, ef_module, utils_module):
            results = retrieve(
                query="bearing inspection",
                persist_dir="/tmp/chroma",
                embedding_model="all-MiniLM-L6-v2",
                top_k=2,
            )

        assert len(results) == 2
        assert isinstance(results[0], RetrievalResult)
        assert results[0].source == "maintenance/bearing.md"
        assert results[0].distance == pytest.approx(0.05)

    def test_returns_empty_on_missing_collection(self) -> None:
        chroma, ef_cls, ef_module, utils_module = _make_chromadb_mock()
        chroma.PersistentClient.return_value.get_collection.side_effect = (
            Exception("Collection not found")
        )

        with _patch_chromadb(chroma, ef_module, utils_module):
            results = retrieve(
                query="pump cavitation",
                persist_dir="/tmp/chroma",
                embedding_model="all-MiniLM-L6-v2",
            )

        assert results == []

    def test_empty_query_returns_empty(self) -> None:
        results = retrieve(
            query="   ",
            persist_dir="/tmp/chroma",
            embedding_model="all-MiniLM-L6-v2",
        )
        assert results == []

    def test_blank_query_returns_empty(self) -> None:
        results = retrieve(
            query="",
            persist_dir="/tmp/chroma",
            embedding_model="all-MiniLM-L6-v2",
        )
        assert results == []

    def test_top_k_capped_by_collection_count(self) -> None:
        chroma, ef_cls, ef_module, utils_module = _make_chromadb_mock()

        mock_collection = MagicMock()
        mock_collection.count.return_value = 1  # only 1 chunk in store
        mock_collection.query.return_value = _make_chroma_response(
            docs=["Only one chunk."],
            metadatas=[{"source": "a.md", "chunk_index": 0}],
            distances=[0.0],
        )
        chroma.PersistentClient.return_value.get_collection.return_value = mock_collection

        with _patch_chromadb(chroma, ef_module, utils_module):
            results = retrieve(
                query="anything",
                persist_dir="/tmp/chroma",
                embedding_model="all-MiniLM-L6-v2",
                top_k=10,
            )

        # n_results passed to query must be min(top_k, count) = 1
        call_kwargs = mock_collection.query.call_args[1]
        assert call_kwargs["n_results"] == 1
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Context-manager helper for sys.modules patching
# ---------------------------------------------------------------------------

from contextlib import contextmanager  # noqa: E402


@contextmanager
def _patch_chromadb(chroma_mock, ef_module, utils_module):
    """Inject the chromadb mock into sys.modules for the duration of the block."""
    saved = {
        k: sys.modules.get(k)
        for k in ("chromadb", "chromadb.utils", "chromadb.utils.embedding_functions")
    }
    sys.modules["chromadb"] = chroma_mock
    sys.modules["chromadb.utils"] = utils_module
    sys.modules["chromadb.utils.embedding_functions"] = ef_module
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
