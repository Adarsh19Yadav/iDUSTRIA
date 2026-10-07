"""
rag — INDUSTRIA-X Maintenance Knowledge RAG
============================================
Public package exports for the RAG subsystem.

Usage (from the agentic layer or backend services)::

    from rag.service import get_rag_service

    svc = get_rag_service()
    results = svc.query("What are the signs of bearing spalling?")
"""

from rag.retriever import RetrievalResult
from rag.service import RAGService, get_rag_service

__all__ = ["RAGService", "RetrievalResult", "get_rag_service"]
