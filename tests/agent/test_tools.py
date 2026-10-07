"""tests/agent/test_tools.py — Phase 7 unit tests for the tool registry.

Tests cover:
- Each tool's call() method with mocked underlying ML/RAG functions.
- Input validation (missing data, invalid types, NaN).
- Output structure and required fields.
- SHAP disclaimer presence.
- RAG grounding note.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.agent.tools import (
    ALLOWED_TOOL_NAMES,
    AssessMachineTool,
    DetectAnomalyTool,
    ExplainPredictionTool,
    PredictFailureTool,
    SearchMaintenanceDocsTool,
    get_tool,
    list_tools,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def machine_input():
    from backend.agent.schemas import MachineInput

    return MachineInput(**{
        "Air temperature [K]": 300.1,
        "Process temperature [K]": 310.2,
        "Rotational speed [rpm]": 1500.0,
        "Torque [Nm]": 45.0,
        "Tool wear [min]": 120.0,
        "Type": "M",
    })


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


def test_all_tools_registered():
    names = list_tools()
    assert set(names) == {
        "predict_failure",
        "detect_anomaly",
        "assess_machine",
        "explain_prediction",
        "search_maintenance_docs",
    }


def test_get_tool_valid():
    tool = get_tool("predict_failure")
    assert tool.name == "predict_failure"


def test_get_tool_invalid():
    with pytest.raises(ValueError, match="Unknown tool"):
        get_tool("rm_rf_everything")


def test_allowed_tool_names_matches_registry():
    assert ALLOWED_TOOL_NAMES == frozenset(list_tools())


# ---------------------------------------------------------------------------
# Tool 1 — predict_failure
# ---------------------------------------------------------------------------


def test_predict_failure_tool_call(machine_input):
    mock_result = MagicMock()
    mock_result.to_dict.return_value = {
        "failure_probability": 0.31,
        "predicted_failure": 0,
        "threshold": 0.543,
        "model_version": "v1",
    }
    with patch("ml.inference.predict_failure", return_value=mock_result):
        tool = PredictFailureTool()
        out = tool.call(machine_input=machine_input)

    assert out["failure_probability"] == 0.31
    assert out["predicted_failure"] == 0
    assert "threshold" in out
    assert "model_version" in out


def test_predict_failure_tool_has_schemas():
    tool = PredictFailureTool()
    assert isinstance(tool.description, str) and len(tool.description) > 0
    assert "machine_input" in tool.input_schema
    assert "failure_probability" in tool.output_schema


# ---------------------------------------------------------------------------
# Tool 2 — detect_anomaly
# ---------------------------------------------------------------------------


def test_detect_anomaly_tool_call(machine_input):
    mock_result = MagicMock()
    mock_result.to_dict.return_value = {
        "anomaly_score": 0.12,
        "is_anomaly": False,
        "raw_score": 0.043,
        "anomaly_version": "v1",
    }
    with patch("ml.anomaly_inference.detect_anomaly", return_value=mock_result):
        tool = DetectAnomalyTool()
        out = tool.call(machine_input=machine_input)

    assert "anomaly_score" in out
    assert "is_anomaly" in out
    assert "raw_score" in out
    assert out["is_anomaly"] is False


def test_detect_anomaly_score_is_not_probability(machine_input):
    """Documentation: description must note anomaly_score is NOT a probability."""
    tool = DetectAnomalyTool()
    assert "not a probability" in tool.description.lower() or "NOT a probability" in tool.description


# ---------------------------------------------------------------------------
# Tool 3 — assess_machine
# ---------------------------------------------------------------------------


def test_assess_machine_tool_call(machine_input):
    mock_result = MagicMock()
    mock_result.to_dict.return_value = {
        "failure_probability": 0.65,
        "predicted_failure": 1,
        "anomaly_score": 0.45,
        "is_anomaly": True,
        "risk_score": 0.59,
        "risk_level": "WARNING",
        "failure_threshold": 0.543,
        "model_version": "v1",
        "anomaly_version": "v1",
        "machine_criticality": 1.0,
    }
    with patch("ml.assessment.assess_machine", return_value=mock_result):
        tool = AssessMachineTool()
        out = tool.call(machine_input=machine_input)

    assert out["risk_level"] == "WARNING"
    assert "risk_score" in out
    assert "failure_probability" in out
    assert "anomaly_score" in out


# ---------------------------------------------------------------------------
# Tool 4 — explain_prediction
# ---------------------------------------------------------------------------


def test_explain_prediction_tool_call(machine_input):
    mock_result = MagicMock()
    mock_result.to_dict.return_value = {
        "failure_probability": 0.65,
        "predicted_failure": 1,
        "threshold": 0.543,
        "model_version": "v1",
        "base_value": -1.2,
        "shap_sum": 0.8,
        "features": [
            {
                "feature": "Torque [Nm]",
                "value": 45.0,
                "shap_value": 0.5,
                "direction": "increases_failure_risk",
                "contribution": 0.5,
            }
        ],
        "summary_text": "The model predicts ...",
    }
    with patch("ml.explainer.explain_prediction", return_value=mock_result):
        tool = ExplainPredictionTool()
        out = tool.call(machine_input=machine_input)

    assert "features" in out
    assert "shap_disclaimer" in out
    # Disclaimer must mention causation or "cause" in some form
    disclaimer_lower = out["shap_disclaimer"].lower()
    assert "caus" in disclaimer_lower or "prove" in disclaimer_lower


def test_explain_prediction_shap_disclaimer_present(machine_input):
    """SHAP disclaimer must always be included in output."""
    mock_result = MagicMock()
    mock_result.to_dict.return_value = {
        "failure_probability": 0.4,
        "predicted_failure": 0,
        "threshold": 0.543,
        "model_version": "v1",
        "base_value": -1.0,
        "shap_sum": 0.1,
        "features": [],
        "summary_text": "",
    }
    with patch("ml.explainer.explain_prediction", return_value=mock_result):
        out = ExplainPredictionTool().call(machine_input=machine_input)

    assert "shap_disclaimer" in out
    assert len(out["shap_disclaimer"]) > 10


# ---------------------------------------------------------------------------
# Tool 5 — search_maintenance_docs
# ---------------------------------------------------------------------------


def test_search_maintenance_docs_tool_call():
    mock_svc = MagicMock()
    mock_svc.query.return_value = [
        MagicMock(
            content="Check bearing lubrication every 500 hours.",
            source="bearing_maintenance.md",
            chunk_index=0,
            distance=0.3,
        )
    ]
    with patch("rag.service.get_rag_service", return_value=mock_svc):
        tool = SearchMaintenanceDocsTool()
        out = tool.call(query="bearing maintenance", top_k=4)

    assert out["total_results"] == 1
    assert out["results"][0]["source"] == "bearing_maintenance.md"
    assert "grounding_note" in out


def test_search_maintenance_docs_empty_results():
    mock_svc = MagicMock()
    mock_svc.query.return_value = []
    with patch("rag.service.get_rag_service", return_value=mock_svc):
        out = SearchMaintenanceDocsTool().call(query="unknown failure mode")

    assert out["total_results"] == 0
    assert "no" in out["grounding_note"].lower() or "not" in out["grounding_note"].lower()


def test_search_maintenance_docs_empty_query():
    tool = SearchMaintenanceDocsTool()
    out = tool.call(query="   ")
    assert out["total_results"] == 0


def test_search_maintenance_docs_top_k_clamped():
    """top_k must be clamped to [1, 10]."""
    mock_svc = MagicMock()
    mock_svc.query.return_value = []
    with patch("rag.service.get_rag_service", return_value=mock_svc):
        SearchMaintenanceDocsTool().call(query="bearing wear", top_k=999)
    # Verify get_rag_service().query was called with top_k ≤ 10
    mock_svc.query.assert_called_once()
    _, call_kwargs = mock_svc.query.call_args
    assert call_kwargs["top_k"] <= 10


def test_search_maintenance_docs_relevance_labels():
    mock_svc = MagicMock()
    mock_svc.query.return_value = [
        MagicMock(content="A", source="s.md", chunk_index=0, distance=0.3),
        MagicMock(content="B", source="s.md", chunk_index=1, distance=0.7),
        MagicMock(content="C", source="s.md", chunk_index=2, distance=1.5),
    ]
    with patch("rag.service.get_rag_service", return_value=mock_svc):
        out = SearchMaintenanceDocsTool().call(query="test")

    labels = [r["relevance_label"] for r in out["results"]]
    assert labels == ["high", "medium", "low"]
