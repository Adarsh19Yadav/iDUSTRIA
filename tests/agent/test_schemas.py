"""tests/agent/test_schemas.py — Phase 7 unit tests for Pydantic schemas.

Tests cover:
- MachineInput validation (all features, Type enum, NaN, inf, missing fields).
- AgentQuery validation (query length, optional machine_input).
- AgentResponse serialisation.
"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from backend.agent.schemas import AgentQuery, AgentResponse, MachineInput


# ---------------------------------------------------------------------------
# MachineInput
# ---------------------------------------------------------------------------


def _valid_kwargs():
    return {
        "Air temperature [K]": 300.1,
        "Process temperature [K]": 310.2,
        "Rotational speed [rpm]": 1500.0,
        "Torque [Nm]": 45.0,
        "Tool wear [min]": 120.0,
        "Type": "M",
    }


def test_machine_input_valid():
    mi = MachineInput(**_valid_kwargs())
    assert mi.air_temperature_k == 300.1
    assert mi.type_ == "M"


def test_machine_input_type_lowercase_normalised():
    kw = _valid_kwargs()
    kw["Type"] = "h"
    mi = MachineInput(**kw)
    assert mi.type_ == "H"


def test_machine_input_type_invalid():
    kw = _valid_kwargs()
    kw["Type"] = "Z"
    with pytest.raises(ValidationError, match="Type"):
        MachineInput(**kw)


def test_machine_input_type_numeric():
    kw = _valid_kwargs()
    kw["Type"] = 42
    with pytest.raises(ValidationError):
        MachineInput(**kw)


def test_machine_input_nan_rejected():
    kw = _valid_kwargs()
    kw["Torque [Nm]"] = float("nan")
    with pytest.raises(ValidationError):
        MachineInput(**kw)


def test_machine_input_inf_rejected():
    kw = _valid_kwargs()
    kw["Rotational speed [rpm]"] = float("inf")
    with pytest.raises(ValidationError):
        MachineInput(**kw)


def test_machine_input_negative_inf_rejected():
    kw = _valid_kwargs()
    kw["Tool wear [min]"] = float("-inf")
    with pytest.raises(ValidationError):
        MachineInput(**kw)


def test_machine_input_missing_torque():
    kw = _valid_kwargs()
    del kw["Torque [Nm]"]
    with pytest.raises(ValidationError):
        MachineInput(**kw)


def test_machine_input_missing_type():
    kw = _valid_kwargs()
    del kw["Type"]
    with pytest.raises(ValidationError):
        MachineInput(**kw)


def test_machine_input_string_number_accepted():
    """Numeric fields should accept string representations of numbers."""
    kw = _valid_kwargs()
    kw["Torque [Nm]"] = "45.5"
    mi = MachineInput(**kw)
    assert mi.torque_nm == 45.5


def test_machine_input_non_numeric_string_rejected():
    kw = _valid_kwargs()
    kw["Torque [Nm]"] = "fast"
    with pytest.raises(ValidationError):
        MachineInput(**kw)


# ---------------------------------------------------------------------------
# AgentQuery
# ---------------------------------------------------------------------------


def test_agent_query_valid_with_machine():
    q = AgentQuery(
        query="What is the failure probability?",
        machine_input=MachineInput(**_valid_kwargs()),
    )
    assert q.query == "What is the failure probability?"
    assert q.machine_input is not None


def test_agent_query_valid_without_machine():
    q = AgentQuery(
        query="What does the knowledge base say about bearing failure?",
    )
    assert q.machine_input is None


def test_agent_query_too_short():
    with pytest.raises(ValidationError):
        AgentQuery(query="Hi")


def test_agent_query_too_long():
    with pytest.raises(ValidationError):
        AgentQuery(query="x" * 1001)


def test_agent_query_empty():
    with pytest.raises(ValidationError):
        AgentQuery(query="")


# ---------------------------------------------------------------------------
# AgentResponse
# ---------------------------------------------------------------------------


def test_agent_response_success():
    r = AgentResponse(
        answer="Risk is WARNING.",
        tools_used=["assess_machine"],
        status="success",
    )
    assert r.status == "success"
    assert r.evidence == []
    assert r.sources == []
    assert r.error_detail is None


def test_agent_response_error():
    r = AgentResponse(
        answer="An error occurred.",
        tools_used=[],
        status="error",
        error_detail="Model artifact not found.",
    )
    assert r.status == "error"
    assert r.error_detail == "Model artifact not found."


def test_agent_response_partial():
    r = AgentResponse(
        answer="Partial results.",
        tools_used=["assess_machine", "explain_prediction"],
        status="partial",
        error_detail="explain_prediction: SHAP error.",
    )
    assert r.status == "partial"


def test_agent_response_invalid_status():
    with pytest.raises(ValidationError):
        AgentResponse(
            answer="Test.",
            tools_used=[],
            status="unknown_status",
        )
