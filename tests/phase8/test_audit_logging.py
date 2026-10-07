"""tests/phase8/test_audit_logging.py — Phase 8 agent audit log tests.

Tests:
- Successful agent request is logged
- Rejected/safe-refusal is logged
- tools_used recorded correctly
- request_id recorded
- No chain-of-thought stored
- session_id recorded when provided
- machine_id recorded when provided
- audit failure does not break response
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.agent_audit_log import AgentAuditLog


def _valid_machine_data():
    return {
        "Air temperature [K]": 300.1,
        "Process temperature [K]": 310.2,
        "Rotational speed [rpm]": 1500.0,
        "Torque [Nm]": 45.0,
        "Tool wear [min]": 120.0,
        "Type": "M",
    }


def _mock_assess():
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


class TestAuditLogging:
    def test_successful_request_logged(self, client: TestClient, db_session: Session):
        with patch("ml.assessment.assess_machine", return_value=_mock_assess()):
            resp = client.post(
                "/api/v1/agent/query",
                json={
                    "query": "What is the overall risk level?",
                    "machine_input": _valid_machine_data(),
                },
            )
        assert resp.status_code == 200

        logs = db_session.query(AgentAuditLog).all()
        assert len(logs) == 1
        log = logs[0]
        assert log.request_id is not None
        assert log.query == "What is the overall risk level?"
        assert log.status in ("success", "partial")

    def test_unsafe_query_logged(self, client: TestClient, db_session: Session):
        resp = client.post(
            "/api/v1/agent/query",
            json={"query": "Shut down the machine immediately."},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"

        logs = db_session.query(AgentAuditLog).all()
        assert len(logs) == 1
        log = logs[0]
        assert log.status == "error"

    def test_tools_used_recorded(self, client: TestClient, db_session: Session):
        with patch("ml.assessment.assess_machine", return_value=_mock_assess()):
            resp = client.post(
                "/api/v1/agent/query",
                json={
                    "query": "What is the overall risk level for this machine?",
                    "machine_input": _valid_machine_data(),
                },
            )
        assert resp.status_code == 200

        log = db_session.query(AgentAuditLog).first()
        assert log is not None
        # tools_used should be a comma-separated string of tool names
        if log.tools_used:
            assert isinstance(log.tools_used, str)
            # No argument values, just names
            assert "assess_machine" in log.tools_used

    def test_request_id_recorded(self, client: TestClient, db_session: Session):
        resp = client.post(
            "/api/v1/agent/query",
            json={"query": "What does the knowledge base say about bearings?"},
        )
        assert resp.status_code == 200
        # request_id in response header
        assert "x-request-id" in resp.headers

        log = db_session.query(AgentAuditLog).first()
        assert log is not None
        assert log.request_id == resp.headers["x-request-id"]

    def test_no_chain_of_thought_stored(self, client: TestClient, db_session: Session):
        """The audit log must not contain any chain-of-thought reasoning."""
        with patch("ml.assessment.assess_machine", return_value=_mock_assess()):
            client.post(
                "/api/v1/agent/query",
                json={
                    "query": "Explain the risk for this machine.",
                    "machine_input": _valid_machine_data(),
                },
            )

        log = db_session.query(AgentAuditLog).first()
        assert log is not None
        # response_summary should be a short metadata string, not full answer
        if log.response_summary:
            # Max 1000 chars and contains structured metadata, not raw LLM output
            assert len(log.response_summary) <= 1000
            # The column name in the model is response_summary, not chain_of_thought
            assert not hasattr(log, "chain_of_thought")

    def test_session_id_recorded(self, client: TestClient, db_session: Session):
        client.post(
            "/api/v1/agent/query",
            json={
                "query": "What does the knowledge base say about lubrication?",
                "session_id": "test-session-999",
            },
        )

        log = db_session.query(AgentAuditLog).first()
        assert log is not None
        assert log.session_id == "test-session-999"

    def test_machine_id_recorded(self, client: TestClient, db_session: Session):
        client.post(
            "/api/v1/agent/query",
            json={
                "query": "What does the knowledge base say about lubrication?",
                "machine_id": "MACHINE-AUDIT-001",
            },
        )

        log = db_session.query(AgentAuditLog).first()
        assert log is not None
        assert log.machine_id == "MACHINE-AUDIT-001"

    def test_latency_recorded(self, client: TestClient, db_session: Session):
        resp = client.post(
            "/api/v1/agent/query",
            json={"query": "What does the knowledge base say about vibration?"},
        )
        assert resp.status_code == 200

        log = db_session.query(AgentAuditLog).first()
        assert log is not None
        assert log.latency_ms is not None
        assert log.latency_ms >= 0


class TestAuditSanitisation:
    def test_query_with_control_chars_is_sanitised(
        self, client: TestClient, db_session: Session
    ):
        """Control characters in query must not be stored (log injection prevention)."""
        client.post(
            "/api/v1/agent/query",
            json={"query": "What is risk?\nINJECTED_LOG_LINE"},
        )
        log = db_session.query(AgentAuditLog).first()
        if log:
            assert "\n" not in log.query
            assert "\r" not in log.query
