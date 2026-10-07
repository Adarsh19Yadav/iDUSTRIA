"""tests/phase8/test_assessment_api.py — Phase 8 Assessment API tests.

Tests:
- POST /api/v1/machines/{id}/assess — ML call, persistence
- GET  /api/v1/machines/{id}/assessments — history
- Missing machine → 404
- Missing ML artifact → 503
- Validation error → 422
- Values persisted correctly
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _mock_assess_result():
    """Build a mock AssessmentResult with realistic values."""
    m = MagicMock()
    m.failure_probability = 0.75
    m.anomaly_score = 0.55
    m.risk_score = 0.69
    m.risk_level = "WARNING"
    m.model_version = "v1"
    m.anomaly_version = "v1"
    m.predicted_failure = 1
    m.is_anomaly = True
    m.failure_threshold = 0.543
    m.machine_criticality = 1.0
    m.to_dict.return_value = {
        "failure_probability": 0.75,
        "anomaly_score": 0.55,
        "risk_score": 0.69,
        "risk_level": "WARNING",
        "model_version": "v1",
    }
    return m


class TestAssessEndpoint:
    def _create_machine(self, client: TestClient) -> dict:
        resp = client.post(
            "/api/v1/machines",
            json={"machine_identifier": "ASSESS-001"},
        )
        assert resp.status_code == 201
        return resp.json()

    def test_assess_success(self, client: TestClient, valid_sensor_payload):
        machine = self._create_machine(client)
        with patch("ml.assessment.assess_machine", return_value=_mock_assess_result()):
            resp = client.post(
                f"/api/v1/machines/{machine['id']}/assess",
                json=valid_sensor_payload,
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["machine_id"] == machine["id"]
        assert body["failure_probability"] == 0.75
        assert body["anomaly_score"] == 0.55
        assert body["risk_score"] == 0.69
        assert body["risk_level"] == "WARNING"
        assert body["model_version"] == "v1"
        assert "created_at" in body

    def test_assess_values_persisted(self, client: TestClient, valid_sensor_payload):
        """Verify that assessed values are retrievable from the history endpoint."""
        machine = self._create_machine(client)
        with patch("ml.assessment.assess_machine", return_value=_mock_assess_result()):
            client.post(
                f"/api/v1/machines/{machine['id']}/assess",
                json=valid_sensor_payload,
            )
        history = client.get(f"/api/v1/machines/{machine['id']}/assessments")
        assert history.status_code == 200
        records = history.json()
        assert len(records) == 1
        assert records[0]["risk_level"] == "WARNING"
        assert records[0]["failure_probability"] == 0.75

    def test_assess_missing_machine(self, client: TestClient, valid_sensor_payload):
        resp = client.post(
            "/api/v1/machines/99999/assess",
            json=valid_sensor_payload,
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_assess_missing_ml_artifact(self, client: TestClient, valid_sensor_payload):
        machine = self._create_machine(client)
        with patch(
            "ml.assessment.assess_machine",
            side_effect=FileNotFoundError("artifact missing"),
        ):
            resp = client.post(
                f"/api/v1/machines/{machine['id']}/assess",
                json=valid_sensor_payload,
            )
        assert resp.status_code == 503
        # Must not expose filesystem paths
        assert "/path/to" not in resp.json().get("detail", "")

    def test_assess_ml_value_error(self, client: TestClient, valid_sensor_payload):
        machine = self._create_machine(client)
        with patch(
            "ml.assessment.assess_machine",
            side_effect=ValueError("invalid type"),
        ):
            resp = client.post(
                f"/api/v1/machines/{machine['id']}/assess",
                json=valid_sensor_payload,
            )
        assert resp.status_code == 422

    def test_assess_invalid_type(self, client: TestClient):
        machine = self._create_machine(client)
        payload = {
            "air_temperature_k": 300.1,
            "process_temperature_k": 310.2,
            "rotational_speed_rpm": 1500.0,
            "torque_nm": 45.0,
            "tool_wear_min": 120.0,
            "type": "Z",  # invalid
        }
        resp = client.post(f"/api/v1/machines/{machine['id']}/assess", json=payload)
        assert resp.status_code == 422

    def test_assess_missing_required_field(self, client: TestClient):
        machine = self._create_machine(client)
        payload = {
            "process_temperature_k": 310.2,
            "rotational_speed_rpm": 1500.0,
            "torque_nm": 45.0,
            "tool_wear_min": 120.0,
            "type": "M",
            # missing air_temperature_k
        }
        resp = client.post(f"/api/v1/machines/{machine['id']}/assess", json=payload)
        assert resp.status_code == 422

    def test_assess_response_schema(self, client: TestClient, valid_sensor_payload):
        machine = self._create_machine(client)
        with patch("ml.assessment.assess_machine", return_value=_mock_assess_result()):
            resp = client.post(
                f"/api/v1/machines/{machine['id']}/assess",
                json=valid_sensor_payload,
            )
        body = resp.json()
        required = {
            "id", "machine_id", "failure_probability", "anomaly_score",
            "risk_score", "risk_level", "model_version", "created_at",
        }
        assert required.issubset(body.keys())


class TestListAssessments:
    def _create_machine(self, client: TestClient, ident: str = "HIST-001") -> dict:
        resp = client.post(
            "/api/v1/machines",
            json={"machine_identifier": ident},
        )
        assert resp.status_code == 201
        return resp.json()

    def test_list_assessments_empty(self, client: TestClient):
        machine = self._create_machine(client, "HIST-EMPTY")
        resp = client.get(f"/api/v1/machines/{machine['id']}/assessments")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_assessments_multiple(self, client: TestClient, valid_sensor_payload):
        machine = self._create_machine(client, "HIST-MULTI")
        with patch("ml.assessment.assess_machine", return_value=_mock_assess_result()):
            for _ in range(3):
                client.post(
                    f"/api/v1/machines/{machine['id']}/assess",
                    json=valid_sensor_payload,
                )
        resp = client.get(f"/api/v1/machines/{machine['id']}/assessments")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_list_assessments_missing_machine(self, client: TestClient):
        resp = client.get("/api/v1/machines/99999/assessments")
        assert resp.status_code == 404

    def test_list_assessments_pagination(self, client: TestClient, valid_sensor_payload):
        machine = self._create_machine(client, "HIST-PAGE")
        with patch("ml.assessment.assess_machine", return_value=_mock_assess_result()):
            for _ in range(5):
                client.post(
                    f"/api/v1/machines/{machine['id']}/assess",
                    json=valid_sensor_payload,
                )
        resp = client.get(f"/api/v1/machines/{machine['id']}/assessments?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
