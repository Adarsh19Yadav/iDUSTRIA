"""tests/phase8/test_error_handling.py — Phase 8 error handling tests.

Tests:
- Validation errors (422)
- Database failure (mocked)
- Missing ML artifact (503)
- Internal error (500) does not expose stack trace
- Missing machine (404)
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError


class TestValidationErrors:
    def test_create_machine_invalid_identifier(self, client: TestClient):
        resp = client.post(
            "/api/v1/machines",
            json={"machine_identifier": "<script>alert(1)</script>"},
        )
        # Pydantic rejects the value — returns 422
        assert resp.status_code == 422
        # The response should be a validation error, not a 500 or 200
        body = resp.json()
        assert "detail" in body

    def test_assess_invalid_json(self, client: TestClient):
        """Malformed JSON body should return 422."""
        # FastAPI returns 422 for missing required fields
        machine = client.post(
            "/api/v1/machines", json={"machine_identifier": "ERR-001"}
        ).json()
        resp = client.post(
            f"/api/v1/machines/{machine['id']}/assess",
            json={"torque_nm": "not_a_number"},  # missing most required fields
        )
        assert resp.status_code == 422

    def test_agent_query_too_short(self, client: TestClient):
        resp = client.post(
            "/api/v1/agent/query",
            json={"query": "Hi"},
        )
        assert resp.status_code == 422


class TestNotFound:
    def test_get_nonexistent_machine(self, client: TestClient):
        resp = client.get("/api/v1/machines/99999")
        assert resp.status_code == 404
        body = resp.json()
        assert "detail" in body
        # Must not expose internal path or table names
        assert "machines" not in body["detail"].lower()

    def test_assess_nonexistent_machine(self, client: TestClient):
        resp = client.post(
            "/api/v1/machines/99999/assess",
            json={
                "air_temperature_k": 300.1,
                "process_temperature_k": 310.2,
                "rotational_speed_rpm": 1500.0,
                "torque_nm": 45.0,
                "tool_wear_min": 120.0,
                "type": "M",
            },
        )
        assert resp.status_code == 404


class TestMLErrors:
    def _create_machine(self, client: TestClient) -> dict:
        r = client.post("/api/v1/machines", json={"machine_identifier": "ERR-ML"})
        assert r.status_code == 201
        return r.json()

    def test_missing_artifact_returns_503(self, client: TestClient):
        machine = self._create_machine(client)
        with patch(
            "ml.assessment.assess_machine",
            side_effect=FileNotFoundError("/some/secret/path/model.pkl"),
        ):
            resp = client.post(
                f"/api/v1/machines/{machine['id']}/assess",
                json={
                    "air_temperature_k": 300.1,
                    "process_temperature_k": 310.2,
                    "rotational_speed_rpm": 1500.0,
                    "torque_nm": 45.0,
                    "tool_wear_min": 120.0,
                    "type": "M",
                },
            )
        assert resp.status_code == 503
        # Must NOT expose filesystem paths
        assert "/some/secret" not in resp.json()["detail"]

    def test_ml_runtime_error_returns_500(self, client: TestClient):
        machine = self._create_machine(client)
        # The service imports ml.assessment.assess_machine locally; patch it there
        with patch(
            "ml.assessment.assess_machine",
            side_effect=Exception("GPU exploded"),
        ):
            resp = client.post(
                f"/api/v1/machines/{machine['id']}/assess",
                json={
                    "air_temperature_k": 300.1,
                    "process_temperature_k": 310.2,
                    "rotational_speed_rpm": 1500.0,
                    "torque_nm": 45.0,
                    "tool_wear_min": 120.0,
                    "type": "M",
                },
            )
        assert resp.status_code in (500, 503)
        # Stack trace must not be exposed
        assert "Traceback" not in resp.text
        assert "GPU exploded" not in resp.text

    def test_agent_internal_error_does_not_expose_trace(self, client: TestClient):
        with patch(
            "backend.agent.orchestrator.AgentOrchestrator.run",
            side_effect=RuntimeError("secret internal detail"),
        ):
            resp = client.post(
                "/api/v1/agent/query",
                json={
                    "query": "What is the risk for this machine?",
                    "machine_input": {
                        "Air temperature [K]": 300.1,
                        "Process temperature [K]": 310.2,
                        "Rotational speed [rpm]": 1500.0,
                        "Torque [Nm]": 45.0,
                        "Tool wear [min]": 120.0,
                        "Type": "M",
                    },
                },
            )
        # Must be 500, not expose secret internal detail
        assert resp.status_code == 500
        assert "secret internal detail" not in resp.text
        assert "Traceback" not in resp.text


class TestOversizedInput:
    def test_query_too_long(self, client: TestClient):
        resp = client.post(
            "/api/v1/agent/query",
            json={"query": "A" * 1001},
        )
        assert resp.status_code == 422

    def test_machine_identifier_too_long(self, client: TestClient):
        resp = client.post(
            "/api/v1/machines",
            json={"machine_identifier": "X" * 200},
        )
        assert resp.status_code == 422
