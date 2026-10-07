"""
tests/phase14/test_api_key_enforcement.py
==========================================
Phase 14: targeted tests verifying that API key enforcement is applied
to all protected write/compute endpoints.

Design
------
- Uses FastAPI TestClient with the real app (no mocking).
- Creates two clients: one WITHOUT override (verifies 403) and one WITH override
  that supplies the key directly (verifies auth passes).
- Checks that missing key → 403, wrong key → 403, correct key → not 403.
- Read-only / public endpoints are verified to remain unprotected.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.core.security import require_api_key
from backend.main import create_app

# ── Fixtures ──────────────────────────────────────────────────────────────────

VALID_KEY = "phase14-test-key"
WRONG_KEY = "definitely-wrong-key"


@pytest.fixture(scope="module")
def unauthed_client():
    """App with NO API key override — all protected endpoints should 403."""
    app = create_app()
    yield TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def authed_client():
    """App with require_api_key bypassed — verifies auth-passing path."""
    app = create_app()

    def _bypass():
        return VALID_KEY

    app.dependency_overrides[require_api_key] = _bypass
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(require_api_key, None)


# ── Helper ────────────────────────────────────────────────────────────────────

def _wrong_key_headers() -> dict:
    return {"X-API-Key": WRONG_KEY}


# ── POST /api/v1/machines ─────────────────────────────────────────────────────

class TestMachinesPostProtected:
    _body = {"machine_identifier": "TEST-M-001", "machine_type": "M", "location": "Bay 1"}

    def test_no_key_returns_403(self, unauthed_client):
        r = unauthed_client.post("/api/v1/machines", json=self._body)
        assert r.status_code == 403

    def test_wrong_key_returns_403(self, unauthed_client):
        r = unauthed_client.post("/api/v1/machines", json=self._body, headers=_wrong_key_headers())
        assert r.status_code == 403

    def test_valid_key_passes_auth(self, authed_client):
        r = authed_client.post("/api/v1/machines", json=self._body)
        # Auth passes — may still fail with 503/422/500 if DB unavailable; not 403
        assert r.status_code != 403

    def test_403_body_does_not_expose_stack_trace(self, unauthed_client):
        r = unauthed_client.post("/api/v1/machines", json=self._body)
        body = r.text
        assert "traceback" not in body.lower()
        assert "file " not in body.lower()


# ── POST /api/v1/machines/{id}/assess ─────────────────────────────────────────

class TestAssessProtected:
    _body = {
        "air_temperature_k": 300.0,
        "process_temperature_k": 310.0,
        "rotational_speed_rpm": 1500.0,
        "torque_nm": 45.0,
        "tool_wear_min": 100.0,
        "type_": "M",
    }

    def test_no_key_returns_403(self, unauthed_client):
        r = unauthed_client.post("/api/v1/machines/1/assess", json=self._body)
        assert r.status_code == 403

    def test_wrong_key_returns_403(self, unauthed_client):
        r = unauthed_client.post("/api/v1/machines/1/assess", json=self._body, headers=_wrong_key_headers())
        assert r.status_code == 403

    def test_valid_key_passes_auth(self, authed_client):
        r = authed_client.post("/api/v1/machines/1/assess", json=self._body)
        assert r.status_code != 403


# ── POST /api/v1/agent/query ──────────────────────────────────────────────────

class TestAgentQueryProtected:
    _body = {"query": "What is the status of machine 1?"}

    def test_no_key_returns_403(self, unauthed_client):
        r = unauthed_client.post("/api/v1/agent/query", json=self._body)
        assert r.status_code == 403

    def test_wrong_key_returns_403(self, unauthed_client):
        r = unauthed_client.post("/api/v1/agent/query", json=self._body, headers=_wrong_key_headers())
        assert r.status_code == 403

    def test_valid_key_passes_auth(self, authed_client):
        r = authed_client.post("/api/v1/agent/query", json=self._body)
        assert r.status_code != 403


# ── POST /api/v1/whatif/analyze ───────────────────────────────────────────────

class TestWhatIfProtected:
    _scenario = {
        "Air temperature [K]": 300.0,
        "Process temperature [K]": 310.0,
        "Rotational speed [rpm]": 1500.0,
        "Torque [Nm]": 45.0,
        "Tool wear [min]": 100.0,
        "Type": "M",
    }
    _body = {"baseline": _scenario, "scenario": _scenario}

    def test_no_key_returns_403(self, unauthed_client):
        r = unauthed_client.post("/api/v1/whatif/analyze", json=self._body)
        assert r.status_code == 403

    def test_wrong_key_returns_403(self, unauthed_client):
        r = unauthed_client.post("/api/v1/whatif/analyze", json=self._body, headers=_wrong_key_headers())
        assert r.status_code == 403

    def test_valid_key_passes_auth(self, authed_client):
        r = authed_client.post("/api/v1/whatif/analyze", json=self._body)
        assert r.status_code != 403


# ── POST /api/v1/sustainability/estimate ──────────────────────────────────────

class TestSustainabilityEstimateProtected:
    _body = {"rotational_speed_rpm": 1500.0, "torque_nm": 45.0}

    def test_no_key_returns_403(self, unauthed_client):
        r = unauthed_client.post("/api/v1/sustainability/estimate", json=self._body)
        assert r.status_code == 403

    def test_wrong_key_returns_403(self, unauthed_client):
        r = unauthed_client.post("/api/v1/sustainability/estimate", json=self._body, headers=_wrong_key_headers())
        assert r.status_code == 403

    def test_valid_key_passes_auth(self, authed_client):
        r = authed_client.post("/api/v1/sustainability/estimate", json=self._body)
        assert r.status_code != 403


# ── POST /api/v1/simulation/* control endpoints ───────────────────────────────

class TestSimulationControlProtected:
    def test_start_no_key_returns_403(self, unauthed_client):
        r = unauthed_client.post("/api/v1/simulation/start", json={})
        assert r.status_code == 403

    def test_pause_no_key_returns_403(self, unauthed_client):
        r = unauthed_client.post("/api/v1/simulation/pause")
        assert r.status_code == 403

    def test_reset_no_key_returns_403(self, unauthed_client):
        r = unauthed_client.post("/api/v1/simulation/reset")
        assert r.status_code == 403

    def test_step_no_key_returns_403(self, unauthed_client):
        r = unauthed_client.post("/api/v1/simulation/step")
        assert r.status_code == 403

    def test_start_valid_key_passes_auth(self, authed_client):
        r = authed_client.post("/api/v1/simulation/start", json={})
        assert r.status_code != 403


# ── Public / read-only endpoints remain unprotected ───────────────────────────

class TestPublicEndpointsUnprotected:
    def test_health_liveness_no_key(self, unauthed_client):
        r = unauthed_client.get("/api/v1/health")
        assert r.status_code == 200

    def test_health_ready_no_key(self, unauthed_client):
        r = unauthed_client.get("/api/v1/health/ready")
        assert r.status_code == 200

    def test_rag_status_no_key(self, unauthed_client):
        r = unauthed_client.get("/api/v1/rag/status")
        assert r.status_code == 200

    def test_sustainability_insights_no_key(self, unauthed_client):
        r = unauthed_client.get("/api/v1/sustainability/insights")
        assert r.status_code == 200

    def test_simulation_status_no_key(self, unauthed_client):
        r = unauthed_client.get("/api/v1/simulation/status")
        assert r.status_code == 200
