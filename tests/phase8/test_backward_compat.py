"""tests/phase8/test_backward_compat.py — Phase 8 backward compatibility tests.

Verifies that ALL Phase 0–7 endpoints remain functional after Phase 8 changes.

Endpoints checked:
- GET  /api/v1/health
- GET  /api/v1/health/ready
- GET  /api/v1/rag/status
- POST /api/v1/rag/query
- POST /api/v1/agent/query
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestPhase1Backward:
    def test_health_liveness_200(self, client: TestClient):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["app"] == "INDUSTRIA-X"

    def test_health_readiness_200(self, client: TestClient):
        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("ready", "degraded")
        assert "checks" in body

    def test_unknown_route_404(self, client: TestClient):
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404


class TestPhase6Backward:
    def test_rag_status_200(self, client: TestClient):
        resp = client.get("/api/v1/rag/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "ready" in body

    def test_rag_query_200(self, client: TestClient):
        svc = MagicMock()
        svc.query.return_value = [
            MagicMock(
                content="Bearing maintenance procedure.",
                source="bearings.md",
                chunk_index=0,
                distance=0.3,
            )
        ]
        with patch("rag.service.get_rag_service", return_value=svc):
            resp = client.post(
                "/api/v1/rag/query",
                json={"question": "How to maintain bearings?"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "results" in body
        assert "total_results" in body


class TestPhase7Backward:
    def _valid_machine_data(self):
        return {
            "Air temperature [K]": 300.1,
            "Process temperature [K]": 310.2,
            "Rotational speed [rpm]": 1500.0,
            "Torque [Nm]": 45.0,
            "Tool wear [min]": 120.0,
            "Type": "M",
        }

    def _mock_assess(self):
        m = MagicMock()
        m.failure_probability = 0.75
        m.anomaly_score = 0.55
        m.risk_score = 0.69
        m.risk_level = "WARNING"
        m.model_version = "v1"
        m.predicted_failure = 1
        m.is_anomaly = True
        m.failure_threshold = 0.543
        m.machine_criticality = 1.0
        m.anomaly_version = "v1"
        m.to_dict.return_value = {
            "failure_probability": 0.75, "predicted_failure": 1, "anomaly_score": 0.55,
            "is_anomaly": True, "risk_score": 0.69, "risk_level": "WARNING",
            "failure_threshold": 0.543, "model_version": "v1", "anomaly_version": "v1",
            "machine_criticality": 1.0,
        }
        return m

    def test_agent_query_200(self, client: TestClient):
        with patch("ml.assessment.assess_machine", return_value=self._mock_assess()):
            resp = client.post(
                "/api/v1/agent/query",
                json={
                    "query": "What is the overall risk for this machine?",
                    "machine_input": self._valid_machine_data(),
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("success", "partial")
        assert "answer" in body
        assert "tools_used" in body
        assert "evidence" in body
        assert "sources" in body

    def test_agent_query_rag_only(self, client: TestClient):
        svc = MagicMock()
        svc.query.return_value = []
        with patch("rag.service.get_rag_service", return_value=svc):
            resp = client.post(
                "/api/v1/agent/query",
                json={"query": "What does the knowledge base say about lubrication?"},
            )
        assert resp.status_code == 200

    def test_agent_unsafe_query_refused(self, client: TestClient):
        resp = client.post(
            "/api/v1/agent/query",
            json={"query": "Shut down machine M-001."},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"

    def test_agent_response_schema_unchanged(self, client: TestClient):
        """Verify Phase 7 response schema is still intact."""
        with patch("ml.assessment.assess_machine", return_value=self._mock_assess()):
            resp = client.post(
                "/api/v1/agent/query",
                json={
                    "query": "What is the risk level for this machine?",
                    "machine_input": self._valid_machine_data(),
                },
            )
        body = resp.json()
        required = {"answer", "tools_used", "evidence", "sources", "status"}
        assert required.issubset(body.keys())

    def test_agent_accepts_session_id(self, client: TestClient):
        """New optional fields must not break Phase 7 clients."""
        resp = client.post(
            "/api/v1/agent/query",
            json={
                "query": "What does the knowledge base say about vibration?",
                "session_id": "sess-123",
                "machine_id": "MACHINE-001",
            },
        )
        assert resp.status_code == 200

    def test_agent_422_on_invalid_input(self, client: TestClient):
        resp = client.post(
            "/api/v1/agent/query",
            json={"query": "Hi"},  # too short
        )
        assert resp.status_code == 422
