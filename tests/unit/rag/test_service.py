"""
tests/unit/rag/test_service.py
===============================
Unit tests for rag/service.py.

Heavy dependencies (ChromaDB, sentence-transformers) are mocked so the tests
run without any network or model-download requirements.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rag.service import RAGService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def svc(tmp_path: Path) -> RAGService:
    return RAGService(
        persist_dir=str(tmp_path / "chroma"),
        embedding_model="all-MiniLM-L6-v2",
        knowledge_base_dir=tmp_path / "kb",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRAGServiceIngest:
    @patch("rag.service.ingest", return_value=12)
    def test_ingest_returns_chunk_count(self, mock_ingest, svc: RAGService) -> None:
        count = svc.ingest()
        assert count == 12

    @patch("rag.service.ingest", return_value=5)
    def test_is_ready_after_ingest(self, mock_ingest, svc: RAGService) -> None:
        assert not svc.is_ready
        svc.ingest()
        assert svc.is_ready

    @patch("rag.service.ingest", return_value=0)
    def test_not_ready_when_ingest_returns_zero(self, mock_ingest, svc: RAGService) -> None:
        svc.ingest()
        assert not svc.is_ready


class TestRAGServiceQuery:
    @patch("rag.service.retrieve")
    @patch("rag.service.ingest", return_value=8)
    def test_query_delegates_to_retrieve(
        self, mock_ingest, mock_retrieve, svc: RAGService
    ) -> None:
        svc.ingest()
        mock_retrieve.return_value = [
            MagicMock(content="Inspect bearings.", source="bearing.md", chunk_index=0, distance=0.1)
        ]
        results = svc.query("bearing inspection", top_k=3)
        mock_retrieve.assert_called_once()
        call_kwargs = mock_retrieve.call_args[1]
        assert call_kwargs["query"] == "bearing inspection"
        assert call_kwargs["top_k"] == 3
        assert len(results) == 1

    @patch("rag.service.retrieve", return_value=[])
    def test_query_before_ingest_returns_empty(self, mock_retrieve, svc: RAGService) -> None:
        # _ingested is False — should still forward the call but log a warning
        results = svc.query("what causes pump cavitation?")
        assert results == []

    @patch("rag.service.retrieve", return_value=[])
    def test_top_k_clamped_to_1(self, mock_retrieve, svc: RAGService) -> None:
        svc.query("test", top_k=0)
        call_kwargs = mock_retrieve.call_args[1]
        assert call_kwargs["top_k"] == 1

    @patch("rag.service.retrieve", return_value=[])
    def test_top_k_clamped_to_10(self, mock_retrieve, svc: RAGService) -> None:
        svc.query("test", top_k=99)
        call_kwargs = mock_retrieve.call_args[1]
        assert call_kwargs["top_k"] == 10
