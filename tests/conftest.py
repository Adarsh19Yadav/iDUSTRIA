"""tests/conftest.py — shared pytest fixtures for INDUSTRIA-X."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import Settings


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Return a Settings instance with test-safe defaults."""
    return Settings(
        APP_ENV="development",
        API_KEY="test-api-key",
        DATABASE_URL="postgresql://industria:industria_pass@localhost:5432/industria_x",
        REDIS_URL="redis://localhost:6379/0",
    )


@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    FastAPI test client.

    Uses the real app with no mocking so that router registration,
    middleware, and schema validation are all exercised.
    """
    return TestClient(app, raise_server_exceptions=True)
