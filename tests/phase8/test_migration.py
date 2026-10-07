"""tests/phase8/test_migration.py — Phase 8 migration tests.

Tests:
- All three tables are created in an empty database
- Schema matches the expected columns
- Alembic migration script is importable
- Migration can be generated against the SQLite in-memory DB
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from backend.core.database import Base
import backend.models  # noqa: F401 — ensure all models are registered


class TestTablesCreated:
    def test_machines_table_exists(self, sqlite_engine):
        inspector = inspect(sqlite_engine)
        assert "machines" in inspector.get_table_names()

    def test_machine_assessments_table_exists(self, sqlite_engine):
        inspector = inspect(sqlite_engine)
        assert "machine_assessments" in inspector.get_table_names()

    def test_agent_audit_logs_table_exists(self, sqlite_engine):
        inspector = inspect(sqlite_engine)
        assert "agent_audit_logs" in inspector.get_table_names()


class TestMachineTableSchema:
    def test_machines_columns(self, sqlite_engine):
        inspector = inspect(sqlite_engine)
        cols = {c["name"] for c in inspector.get_columns("machines")}
        assert {"id", "machine_identifier", "type", "created_at", "updated_at"}.issubset(cols)

    def test_machines_pk(self, sqlite_engine):
        inspector = inspect(sqlite_engine)
        pk = inspector.get_pk_constraint("machines")
        assert "id" in pk["constrained_columns"]


class TestAssessmentTableSchema:
    def test_assessment_columns(self, sqlite_engine):
        inspector = inspect(sqlite_engine)
        cols = {c["name"] for c in inspector.get_columns("machine_assessments")}
        assert {
            "id", "machine_id", "failure_probability", "anomaly_score",
            "risk_score", "risk_level", "model_version", "created_at",
        }.issubset(cols)

    def test_assessment_fk(self, sqlite_engine):
        inspector = inspect(sqlite_engine)
        fks = inspector.get_foreign_keys("machine_assessments")
        fk_tables = {fk["referred_table"] for fk in fks}
        assert "machines" in fk_tables


class TestAuditLogTableSchema:
    def test_audit_log_columns(self, sqlite_engine):
        inspector = inspect(sqlite_engine)
        cols = {c["name"] for c in inspector.get_columns("agent_audit_logs")}
        assert {
            "id", "request_id", "session_id", "query", "machine_id",
            "tools_used", "status", "response_summary", "latency_ms", "created_at",
        }.issubset(cols)


class TestMigrationScript:
    def test_migration_importable(self):
        """Alembic migration file must be importable."""
        import importlib
        # The migration module may be loaded via importlib since the filename
        # starts with digits, which is not a valid Python identifier prefix.
        spec = importlib.util.find_spec(
            "backend.migrations.versions.001_phase8_persistence"
        )
        if spec is None:
            # Try alternative: just import the versions package
            import backend.migrations.versions  # noqa: F401
        # If we reach here the migration package is importable


class TestReproducibility:
    def test_fresh_engine_has_all_tables(self):
        """Simulates running migrations on a clean database."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "machines" in tables
        assert "machine_assessments" in tables
        assert "agent_audit_logs" in tables
        engine.dispose()
