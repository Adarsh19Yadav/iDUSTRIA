"""tests/phase8/conftest.py — shared fixtures for Phase 8 tests.

Uses SQLite in-memory for fast, isolated unit tests.
No live PostgreSQL required.

SQLite in-memory notes
----------------------
SQLite `:///:memory:` databases are per-connection; a second connection
gets an empty database.  We use StaticPool so every SQLAlchemy connection
(including the one used by the FastAPI TestClient) shares the same
single in-memory database instance.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.core.database import Base, get_db
from backend.main import create_app


# ── In-memory SQLite engine ───────────────────────────────────────────────────

@pytest.fixture(scope="function")
def sqlite_engine():
    """Create a fresh in-memory SQLite engine per test, using StaticPool.

    StaticPool ensures that every connection goes to the same in-memory
    database, so tables created by create_all() are visible to the session
    used by the FastAPI TestClient.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(sqlite_engine) -> Session:
    """Provide a transactional SQLAlchemy session backed by in-memory SQLite."""
    SessionLocal = sessionmaker(bind=sqlite_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


_TEST_API_KEY = "phase8-test-key"


@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    """
    FastAPI TestClient with the in-memory database injected.

    Overrides the get_db dependency AND the agent audit DB dependency
    so tests never touch PostgreSQL.

    Phase 14: also overrides require_api_key so existing Phase 8 tests
    continue to pass without needing to supply an X-API-Key header.
    The Phase 14 test suite (tests/phase14/) tests the key enforcement itself.
    """
    from backend.api.agent import _get_db_for_audit  # noqa: PLC0415
    from backend.core.security import require_api_key  # noqa: PLC0415

    app = create_app()

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    def _override_require_api_key():
        """Bypass API key check in Phase 8 tests — key enforcement tested separately."""
        return _TEST_API_KEY

    app.dependency_overrides[get_db] = _override_get_db
    # Also override the agent-specific audit DB dependency
    app.dependency_overrides[_get_db_for_audit] = _override_get_db
    # Phase 14: bypass API key enforcement in Phase 8 tests
    app.dependency_overrides[require_api_key] = _override_require_api_key
    return TestClient(app, raise_server_exceptions=False)


# ── Reusable valid machine data ───────────────────────────────────────────────

@pytest.fixture
def valid_machine_payload():
    return {"machine_identifier": "MACHINE-001", "type": "CNC_LATHE"}


@pytest.fixture
def valid_sensor_payload():
    return {
        "air_temperature_k": 300.1,
        "process_temperature_k": 310.2,
        "rotational_speed_rpm": 1500.0,
        "torque_nm": 45.0,
        "tool_wear_min": 120.0,
        "type": "M",
    }
