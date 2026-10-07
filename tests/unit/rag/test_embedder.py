"""
tests/unit/rag/test_embedder.py
================================
Unit tests for rag/embedder.py — document loading and chunking logic.

These tests do NOT require ChromaDB or sentence-transformers to be installed.
The ``ingest`` function is tested separately (integration level) because it
requires the vector store dependencies.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rag.embedder import Document, chunk_document, chunk_documents, load_documents


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_knowledge_base(tmp_path: Path) -> Path:
    """Create a minimal temporary knowledge base directory."""
    maintenance = tmp_path / "maintenance"
    maintenance.mkdir()
    (maintenance / "bearing.md").write_text(
        "# Bearing Guide\n\nInspect bearings every 1000 hours.\n\nReplace if worn.",
        encoding="utf-8",
    )

    failure_modes = tmp_path / "failure_modes"
    failure_modes.mkdir()
    (failure_modes / "spalling.md").write_text(
        "# Spalling\n\nSpalling is surface fatigue on raceways.",
        encoding="utf-8",
    )
    return tmp_path


# ---------------------------------------------------------------------------
# load_documents
# ---------------------------------------------------------------------------


class TestLoadDocuments:
    def test_loads_all_md_files(self, tmp_knowledge_base: Path) -> None:
        docs = load_documents(tmp_knowledge_base)
        assert len(docs) == 2

    def test_document_has_content(self, tmp_knowledge_base: Path) -> None:
        docs = load_documents(tmp_knowledge_base)
        for doc in docs:
            assert doc.content.strip()

    def test_source_is_relative_posix_path(self, tmp_knowledge_base: Path) -> None:
        docs = load_documents(tmp_knowledge_base)
        sources = {doc.source for doc in docs}
        assert "maintenance/bearing.md" in sources
        assert "failure_modes/spalling.md" in sources

    def test_missing_directory_returns_empty(self, tmp_path: Path) -> None:
        docs = load_documents(tmp_path / "does_not_exist")
        assert docs == []

    def test_ignores_non_md_files(self, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").write_text("not markdown", encoding="utf-8")
        docs = load_documents(tmp_path)
        assert docs == []


# ---------------------------------------------------------------------------
# chunk_document
# ---------------------------------------------------------------------------


class TestChunkDocument:
    def test_short_document_is_single_chunk(self) -> None:
        doc = Document(content="Short text.", source="test.md")
        chunks = chunk_document(doc, chunk_size=500)
        assert len(chunks) == 1
        assert chunks[0].content == "Short text."
        assert chunks[0].chunk_index == 0

    def test_long_document_produces_multiple_chunks(self) -> None:
        # ~1200 chars, chunk_size=500
        content = ("A " * 600).strip()
        doc = Document(content=content, source="test.md")
        chunks = chunk_document(doc, chunk_size=500, overlap=50)
        assert len(chunks) > 1

    def test_chunk_indices_are_sequential(self) -> None:
        content = ("Word " * 300).strip()
        doc = Document(content=content, source="test.md")
        chunks = chunk_document(doc, chunk_size=200, overlap=20)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunk_source_preserved(self) -> None:
        doc = Document(content="Some content " * 50, source="maintenance/pump.md")
        chunks = chunk_document(doc, chunk_size=100, overlap=10)
        for chunk in chunks:
            assert chunk.source == "maintenance/pump.md"

    def test_no_empty_chunks(self) -> None:
        doc = Document(content=("Para one.\n\n" * 30), source="test.md")
        chunks = chunk_document(doc, chunk_size=300, overlap=30)
        for chunk in chunks:
            assert chunk.content.strip()


# ---------------------------------------------------------------------------
# chunk_documents
# ---------------------------------------------------------------------------


class TestChunkDocuments:
    def test_empty_input(self) -> None:
        assert chunk_documents([]) == []

    def test_total_chunks_greater_than_doc_count(self) -> None:
        long_content = "paragraph text\n\n" * 50
        docs = [
            Document(content=long_content, source="a.md"),
            Document(content=long_content, source="b.md"),
        ]
        chunks = chunk_documents(docs, chunk_size=100, overlap=10)
        assert len(chunks) >= len(docs)
