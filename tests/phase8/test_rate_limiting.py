"""tests/phase8/test_rate_limiting.py — Phase 8 rate limiting tests.

Tests:
- Requests within limit are allowed
- Requests exceeding limit return 429
- Redis unavailable → graceful bypass (requests still allowed)
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


class TestRateLimiting:
    def test_requests_within_limit_allowed(self, client: TestClient):
        """With Redis mocked to allow, requests should succeed."""
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 1  # first request, well within limit
        mock_redis.expire.return_value = True

        with patch("backend.core.rate_limiter.get_redis", return_value=mock_redis):
            resp = client.post(
                "/api/v1/agent/query",
                json={"query": "What does the knowledge base say about bearings?"},
            )
        assert resp.status_code == 200

    def test_rate_limit_exceeded_returns_429(self, client: TestClient):
        """When the Redis counter exceeds the limit, expect 429."""
        mock_redis = MagicMock()
        # Return a count that exceeds any configured limit
        mock_redis.incr.return_value = 10_000
        mock_redis.expire.return_value = True

        with patch("backend.core.rate_limiter.get_redis", return_value=mock_redis):
            resp = client.post(
                "/api/v1/agent/query",
                json={"query": "What does the knowledge base say about bearings?"},
            )
        assert resp.status_code == 429
        body = resp.json()
        assert "rate limit" in body["detail"].lower()

    def test_rate_limit_exceeded_has_retry_after_header(self, client: TestClient):
        """429 response should include Retry-After header."""
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 10_000
        mock_redis.expire.return_value = True

        with patch("backend.core.rate_limiter.get_redis", return_value=mock_redis):
            resp = client.post(
                "/api/v1/agent/query",
                json={"query": "What does the knowledge base say about bearings?"},
            )
        assert resp.status_code == 429
        assert "retry-after" in resp.headers

    def test_redis_unavailable_fails_open(self, client: TestClient):
        """When Redis is unavailable, rate limiting is bypassed gracefully."""
        with patch(
            "backend.core.rate_limiter.get_redis",
            side_effect=ConnectionError("Redis unavailable"),
        ):
            resp = client.post(
                "/api/v1/agent/query",
                json={"query": "What does the knowledge base say about lubrication?"},
            )
        # Request should succeed — rate limiting fails open
        assert resp.status_code == 200

    def test_assess_endpoint_rate_limited(self, client: TestClient):
        """The assess endpoint is also protected."""
        # Create a machine first
        machine_resp = client.post(
            "/api/v1/machines", json={"machine_identifier": "RL-TEST-001"}
        )
        assert machine_resp.status_code == 201
        machine_id = machine_resp.json()["id"]

        mock_redis = MagicMock()
        mock_redis.incr.return_value = 10_000
        mock_redis.expire.return_value = True

        with patch("backend.core.rate_limiter.get_redis", return_value=mock_redis):
            resp = client.post(
                f"/api/v1/machines/{machine_id}/assess",
                json={
                    "air_temperature_k": 300.1,
                    "process_temperature_k": 310.2,
                    "rotational_speed_rpm": 1500.0,
                    "torque_nm": 45.0,
                    "tool_wear_min": 120.0,
                    "type": "M",
                },
            )
        assert resp.status_code == 429
