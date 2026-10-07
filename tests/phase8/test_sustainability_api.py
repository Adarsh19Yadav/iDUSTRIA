"""
tests/phase8/test_sustainability_api.py
========================================
Phase 10: Targeted API tests for POST /api/v1/sustainability/estimate
and GET /api/v1/sustainability/insights.

Uses the same in-memory SQLite client fixture from conftest.py.
No PostgreSQL or Redis required.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestSustainabilityEstimate:
    """POST /api/v1/sustainability/estimate"""

    def test_estimate_success_returns_200(self, client: TestClient):
        resp = client.post(
            "/api/v1/sustainability/estimate",
            json={
                "rotational_speed_rpm": 1500,
                "torque_nm": 45,
                "operating_hours": 8,
            },
        )
        assert resp.status_code == 200

    def test_estimate_response_structure(self, client: TestClient):
        """Response must contain all required estimated fields."""
        resp = client.post(
            "/api/v1/sustainability/estimate",
            json={
                "rotational_speed_rpm": 1500,
                "torque_nm": 45,
                "operating_hours": 8,
            },
        )
        body = resp.json()
        assert "estimated_mechanical_power_kw" in body
        assert "estimated_electrical_power_kw" in body
        assert "estimated_energy_kwh" in body
        assert "estimated_co2e_kg" in body
        assert "assumptions" in body

    def test_estimate_assumptions_disclosure(self, client: TestClient):
        """Assumptions must contain the required disclaimer text."""
        resp = client.post(
            "/api/v1/sustainability/estimate",
            json={"rotational_speed_rpm": 1200, "torque_nm": 30, "operating_hours": 4},
        )
        assumptions = resp.json()["assumptions"]
        assert "NOT measured" in assumptions["disclaimer"]
        assert "efficiency" in assumptions
        assert "emission_factor_kg_co2e_per_kwh" in assumptions

    def test_estimate_values_are_positive(self, client: TestClient):
        """All estimated numeric outputs must be > 0 for valid positive inputs."""
        resp = client.post(
            "/api/v1/sustainability/estimate",
            json={"rotational_speed_rpm": 1500, "torque_nm": 45, "operating_hours": 8},
        )
        body = resp.json()
        assert body["estimated_mechanical_power_kw"] > 0
        assert body["estimated_electrical_power_kw"] > 0
        assert body["estimated_energy_kwh"] > 0
        assert body["estimated_co2e_kg"] > 0

    def test_estimate_custom_efficiency(self, client: TestClient):
        """Lower efficiency should produce higher estimated electrical power."""
        base = {
            "rotational_speed_rpm": 1500,
            "torque_nm": 45,
            "operating_hours": 8,
        }
        r_default = client.post(
            "/api/v1/sustainability/estimate",
            json={**base, "efficiency": 0.88},
        ).json()
        r_low = client.post(
            "/api/v1/sustainability/estimate",
            json={**base, "efficiency": 0.70},
        ).json()
        assert r_low["estimated_electrical_power_kw"] > r_default["estimated_electrical_power_kw"]

    def test_estimate_custom_emission_factor(self, client: TestClient):
        """Higher emission factor should increase estimated CO2e."""
        base = {
            "rotational_speed_rpm": 1500,
            "torque_nm": 45,
            "operating_hours": 8,
        }
        r_low = client.post(
            "/api/v1/sustainability/estimate",
            json={**base, "emission_factor_kg_co2e_per_kwh": 0.2},
        ).json()
        r_high = client.post(
            "/api/v1/sustainability/estimate",
            json={**base, "emission_factor_kg_co2e_per_kwh": 0.8},
        ).json()
        assert r_high["estimated_co2e_kg"] > r_low["estimated_co2e_kg"]

    def test_estimate_invalid_zero_rpm(self, client: TestClient):
        """Zero RPM must return 422 validation error."""
        resp = client.post(
            "/api/v1/sustainability/estimate",
            json={"rotational_speed_rpm": 0, "torque_nm": 45, "operating_hours": 8},
        )
        assert resp.status_code == 422

    def test_estimate_invalid_negative_torque(self, client: TestClient):
        """Negative torque must return 422 validation error."""
        resp = client.post(
            "/api/v1/sustainability/estimate",
            json={"rotational_speed_rpm": 1500, "torque_nm": -5, "operating_hours": 8},
        )
        assert resp.status_code == 422

    def test_estimate_invalid_machine_type(self, client: TestClient):
        """Invalid machine_type must return 422."""
        resp = client.post(
            "/api/v1/sustainability/estimate",
            json={
                "rotational_speed_rpm": 1500,
                "torque_nm": 45,
                "operating_hours": 8,
                "machine_type": "X",
            },
        )
        assert resp.status_code == 422

    def test_estimate_with_valid_machine_type(self, client: TestClient):
        """Valid machine_type 'H' should be accepted and echoed in response."""
        resp = client.post(
            "/api/v1/sustainability/estimate",
            json={
                "rotational_speed_rpm": 1500,
                "torque_nm": 45,
                "operating_hours": 8,
                "machine_type": "H",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["machine_type"] == "H"


class TestSustainabilityInsights:
    """GET /api/v1/sustainability/insights"""

    def test_insights_returns_200(self, client: TestClient):
        resp = client.get("/api/v1/sustainability/insights")
        assert resp.status_code == 200

    def test_insights_response_structure(self, client: TestClient):
        body = client.get("/api/v1/sustainability/insights").json()
        assert "insights" in body
        assert "disclaimer" in body
        assert isinstance(body["insights"], list)
        assert len(body["insights"]) > 0

    def test_insights_disclaimer_present(self, client: TestClient):
        body = client.get("/api/v1/sustainability/insights").json()
        assert len(body["disclaimer"]) > 0
