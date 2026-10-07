"""
tests/integration/test_health.py
=================================
Integration tests for the health check endpoints.

These tests use the FastAPI TestClient and test the actual
endpoints without mocking the application logic.
DB and Redis connectivity is tested but failures are handled
gracefully — the endpoints must respond regardless of whether
PostgreSQL/Redis are running.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app, raise_server_exceptions=True)


class TestLivenessEndpoint:
    def test_liveness_returns_200(self, client: TestClient):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_liveness_response_schema(self, client: TestClient):
        response = client.get("/api/v1/health")
        body = response.json()
        assert body["status"] == "ok"
        assert "timestamp" in body
        assert "version" in body
        assert "environment" in body
        assert "python" in body
        assert "platform" in body
        assert "app" in body

    def test_liveness_app_name(self, client: TestClient):
        response = client.get("/api/v1/health")
        body = response.json()
        assert body["app"] == "INDUSTRIA-X"

    def test_liveness_version(self, client: TestClient):
        response = client.get("/api/v1/health")
        body = response.json()
        assert body["version"] == "0.1.0"

    def test_liveness_environment_is_string(self, client: TestClient):
        response = client.get("/api/v1/health")
        body = response.json()
        assert isinstance(body["environment"], str)


class TestReadinessEndpoint:
    def test_readiness_returns_200(self, client: TestClient):
        """Readiness always returns 200; status field indicates health."""
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200

    def test_readiness_response_schema(self, client: TestClient):
        response = client.get("/api/v1/health/ready")
        body = response.json()
        assert "status" in body
        assert body["status"] in ("ready", "degraded")
        assert "checks" in body
        assert "database" in body["checks"]
        assert "redis" in body["checks"]

    def test_readiness_no_pending_services_field(self, client: TestClient):
        """Phase 14: stale pending_services field removed."""
        response = client.get("/api/v1/health/ready")
        body = response.json()
        assert "pending_services" not in body

    def test_readiness_checks_are_valid_values(self, client: TestClient):
        response = client.get("/api/v1/health/ready")
        body = response.json()
        valid_values = {"ok", "unavailable"}
        assert body["checks"]["database"] in valid_values
        assert body["checks"]["redis"] in valid_values

    def test_readiness_timestamp_is_iso8601(self, client: TestClient):
        from datetime import datetime
        response = client.get("/api/v1/health/ready")
        body = response.json()
        # Should not raise
        datetime.fromisoformat(body["timestamp"])


class TestAPIStructure:
    def test_openapi_schema_available(self, client: TestClient):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

    def test_docs_available(self, client: TestClient):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_unknown_route_returns_404(self, client: TestClient):
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
