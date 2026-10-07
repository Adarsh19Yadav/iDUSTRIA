"""tests/phase8/test_request_id.py — Phase 8 request ID tests.

Tests:
- Request ID generated when absent
- Request ID preserved when client supplies it
- X-Request-ID returned in response header
- Invalid/unsafe client IDs are rejected and a new one generated
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class TestRequestID:
    def test_request_id_generated_when_absent(self, client: TestClient):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert "x-request-id" in resp.headers
        rid = resp.headers["x-request-id"]
        assert _UUID_RE.match(rid), f"Expected UUID, got {rid!r}"

    def test_request_id_preserved_when_supplied(self, client: TestClient):
        custom_id = "test-request-abc-12345678"
        resp = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
        assert resp.status_code == 200
        assert resp.headers["x-request-id"] == custom_id

    def test_unsafe_request_id_replaced(self, client: TestClient):
        """Unsafe characters in client-supplied ID should be ignored."""
        unsafe_id = "../../etc/passwd"
        resp = client.get("/api/v1/health", headers={"X-Request-ID": unsafe_id})
        assert resp.status_code == 200
        returned_id = resp.headers["x-request-id"]
        # Should NOT echo the unsafe path
        assert returned_id != unsafe_id
        # Should be a fresh UUID instead
        assert _UUID_RE.match(returned_id)

    def test_request_id_on_post_endpoint(self, client: TestClient):
        resp = client.post(
            "/api/v1/agent/query",
            json={"query": "What does the knowledge base say about bearings?"},
        )
        assert resp.status_code == 200
        assert "x-request-id" in resp.headers

    def test_different_requests_get_different_ids(self, client: TestClient):
        resp1 = client.get("/api/v1/health")
        resp2 = client.get("/api/v1/health")
        id1 = resp1.headers["x-request-id"]
        id2 = resp2.headers["x-request-id"]
        assert id1 != id2

    def test_client_supplied_valid_uuid(self, client: TestClient):
        uuid_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        resp = client.get("/api/v1/health", headers={"X-Request-ID": uuid_id})
        assert resp.headers["x-request-id"] == uuid_id

    def test_request_id_too_short_replaced(self, client: TestClient):
        """IDs shorter than 8 chars are rejected (too short to be meaningful)."""
        short_id = "abc"
        resp = client.get("/api/v1/health", headers={"X-Request-ID": short_id})
        returned_id = resp.headers["x-request-id"]
        # Short ID fails the regex, so a new one is generated
        assert returned_id != short_id
