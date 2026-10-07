"""tests/phase8/test_models.py — Phase 8 database model tests.

Tests:
- Machine model creation and persistence
- MachineAssessment model creation and FK relationship
- AgentAuditLog model creation
- Missing record retrieval returns None
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.models.machine import Machine
from backend.models.machine_assessment import MachineAssessment
from backend.models.agent_audit_log import AgentAuditLog


class TestMachineModel:
    def test_create_machine(self, db_session: Session):
        machine = Machine(machine_identifier="M-001", type="CNC")
        db_session.add(machine)
        db_session.commit()
        db_session.refresh(machine)

        assert machine.id is not None
        assert machine.machine_identifier == "M-001"
        assert machine.type == "CNC"
        assert machine.created_at is not None
        assert machine.updated_at is not None

    def test_machine_without_type(self, db_session: Session):
        machine = Machine(machine_identifier="M-002")
        db_session.add(machine)
        db_session.commit()
        assert machine.type is None

    def test_machine_repr(self, db_session: Session):
        machine = Machine(machine_identifier="M-003")
        db_session.add(machine)
        db_session.commit()
        assert "M-003" in repr(machine)

    def test_machine_lookup_by_id(self, db_session: Session):
        machine = Machine(machine_identifier="M-004")
        db_session.add(machine)
        db_session.commit()

        fetched = db_session.get(Machine, machine.id)
        assert fetched is not None
        assert fetched.machine_identifier == "M-004"

    def test_missing_machine_returns_none(self, db_session: Session):
        result = db_session.get(Machine, 99999)
        assert result is None


class TestMachineAssessmentModel:
    def test_create_assessment(self, db_session: Session):
        machine = Machine(machine_identifier="M-010")
        db_session.add(machine)
        db_session.commit()

        assessment = MachineAssessment(
            machine_id=machine.id,
            failure_probability=0.75,
            anomaly_score=0.55,
            risk_score=0.69,
            risk_level="WARNING",
            model_version="v1",
        )
        db_session.add(assessment)
        db_session.commit()
        db_session.refresh(assessment)

        assert assessment.id is not None
        assert assessment.machine_id == machine.id
        assert assessment.failure_probability == 0.75
        assert assessment.risk_level == "WARNING"
        assert assessment.created_at is not None

    def test_assessment_relationship(self, db_session: Session):
        machine = Machine(machine_identifier="M-011")
        db_session.add(machine)
        db_session.commit()

        for i in range(3):
            a = MachineAssessment(
                machine_id=machine.id,
                failure_probability=0.1 * i,
                anomaly_score=0.2,
                risk_score=0.1 * i,
                risk_level="NORMAL",
                model_version="v1",
            )
            db_session.add(a)
        db_session.commit()
        db_session.refresh(machine)

        assert len(machine.assessments) == 3

    def test_assessment_repr(self, db_session: Session):
        machine = Machine(machine_identifier="M-012")
        db_session.add(machine)
        db_session.commit()

        assessment = MachineAssessment(
            machine_id=machine.id,
            failure_probability=0.5,
            anomaly_score=0.3,
            risk_score=0.44,
            risk_level="WARNING",
            model_version="v1",
        )
        db_session.add(assessment)
        db_session.commit()
        assert "WARNING" in repr(assessment)


class TestAgentAuditLogModel:
    def test_create_audit_log(self, db_session: Session):
        log = AgentAuditLog(
            request_id="req-001",
            query="What is the risk?",
            status="success",
            tools_used="assess_machine",
            response_summary="Risk is WARNING.",
            latency_ms=123,
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        assert log.id is not None
        assert log.request_id == "req-001"
        assert log.status == "success"
        assert log.latency_ms == 123
        assert log.created_at is not None

    def test_audit_log_nullable_fields(self, db_session: Session):
        log = AgentAuditLog(
            request_id="req-002",
            query="Hello?",
            status="error",
        )
        db_session.add(log)
        db_session.commit()

        assert log.session_id is None
        assert log.machine_id is None
        assert log.tools_used is None
        assert log.response_summary is None
        assert log.latency_ms is None

    def test_audit_log_with_session_id(self, db_session: Session):
        log = AgentAuditLog(
            request_id="req-003",
            query="Status?",
            status="success",
            session_id="sess-abc",
        )
        db_session.add(log)
        db_session.commit()
        assert log.session_id == "sess-abc"

    def test_audit_log_repr(self, db_session: Session):
        log = AgentAuditLog(
            request_id="req-004",
            query="Risk?",
            status="success",
        )
        db_session.add(log)
        db_session.commit()
        assert "req-004" in repr(log)
