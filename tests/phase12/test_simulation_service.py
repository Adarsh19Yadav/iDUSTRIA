"""
tests/phase12/test_simulation_service.py
==========================================
Phase 12: Targeted unit tests for the simulation service.

Tests cover:
 1. Initialization — engine starts in IDLE state
 2. First step (requires ML artifacts + dataset)
 3. Sequential stepping produces incrementing steps
 4. Reset returns to IDLE, clears history
 5. Pause/start state transitions
 6. End-of-dataset detection (mocked rows)
 7. SimulationEvent structure correctness
 8. Alert generation — RISK_CRITICAL transition
 9. Alert generation — ANOMALY transition
10. Alert: failure threshold crossing
11. Dataset unavailable → FileNotFoundError
12. No fabricated fallback data on missing dataset
13. Engine state serialization (status dict keys)
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from backend.services.simulation_service import (
    SimulationEngine,
    SimulationEvent,
    SimulationState,
    get_simulation_engine,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def fresh_engine() -> SimulationEngine:
    """A fresh SimulationEngine instance (not the module singleton)."""
    return SimulationEngine()


def _make_mock_row(
    type_="M",
    air=300.0, process=310.0, rpm=1500.0, torque=45.0, wear=100.0,
    product_id="M-001",
) -> dict:
    return {
        "Type": type_,
        "Air temperature [K]": air,
        "Process temperature [K]": process,
        "Rotational speed [rpm]": rpm,
        "Torque [Nm]": torque,
        "Tool wear [min]": wear,
        "Product ID": product_id,
    }


def _mock_assess_result(
    failure_prob=0.1, anomaly_score=0.0, risk_score=0.1,
    risk_level="NORMAL", is_anomaly=False, predicted_failure=0,
    failure_threshold=0.543, model_version="v1",
):
    m = MagicMock()
    m.failure_probability = failure_prob
    m.anomaly_score = anomaly_score
    m.risk_score = risk_score
    m.risk_level = risk_level
    m.is_anomaly = is_anomaly
    m.predicted_failure = predicted_failure
    m.failure_threshold = failure_threshold
    m.model_version = model_version
    return m


# ── State and init tests ──────────────────────────────────────────────────────

def test_initial_state_idle(fresh_engine):
    """Engine starts IDLE, no current event, no history."""
    assert fresh_engine.state == SimulationState.IDLE
    assert fresh_engine.current_event is None
    assert fresh_engine.history == []
    assert fresh_engine.alerts == []
    assert fresh_engine.current_step == 0


def test_singleton_returns_same_instance():
    """get_simulation_engine() returns the same object each call."""
    e1 = get_simulation_engine()
    e2 = get_simulation_engine()
    assert e1 is e2


# ── Dataset unavailable ───────────────────────────────────────────────────────

def test_start_missing_dataset_raises(fresh_engine):
    """If dataset CSV is absent, start() raises FileNotFoundError — no fake data."""
    with patch("ml.data.loader.load_raw", side_effect=FileNotFoundError("no csv")):
        with pytest.raises(FileNotFoundError):
            fresh_engine.start()


def test_step_missing_dataset_raises(fresh_engine):
    """If dataset CSV is absent, step() surfaces the error — no fabricated fallback."""
    with patch("ml.data.loader.load_raw", side_effect=FileNotFoundError("no csv")):
        with pytest.raises(FileNotFoundError):
            fresh_engine.step()


# ── Step and state tests (mocked dataset + ML) ────────────────────────────────

def _start_engine_with_mock_rows(engine, rows):
    """Inject mock rows directly and set state to RUNNING."""
    engine._rows = rows
    engine._total_rows = len(rows)
    engine._state = SimulationState.RUNNING


@pytest.mark.ml_artifacts
def test_first_step_returns_event(fresh_engine):
    """First step on real dataset returns a correctly structured SimulationEvent."""
    fresh_engine.start()
    event = fresh_engine.step()
    assert isinstance(event, SimulationEvent)
    assert event.simulation_step == 1
    assert event.simulated_time_label == "Step 1"
    assert event.risk_level in {"NORMAL", "WARNING", "CRITICAL"}
    assert 0.0 <= event.failure_probability <= 1.0
    assert 0.0 <= event.anomaly_score <= 1.0
    assert 0.0 <= event.risk_score <= 1.0
    assert isinstance(event.is_anomaly, bool)


@pytest.mark.ml_artifacts
def test_sequential_steps_increment(fresh_engine):
    """Each step increments simulation_step by 1."""
    fresh_engine.start()
    e1 = fresh_engine.step()
    e2 = fresh_engine.step()
    e3 = fresh_engine.step()
    assert e1.simulation_step == 1
    assert e2.simulation_step == 2
    assert e3.simulation_step == 3
    assert fresh_engine.current_step == 3


@pytest.mark.ml_artifacts
def test_reset_clears_state(fresh_engine):
    """Reset returns engine to IDLE and clears history."""
    fresh_engine.start()
    fresh_engine.step()
    fresh_engine.reset()
    assert fresh_engine.state == SimulationState.IDLE
    assert fresh_engine.current_step == 0
    assert fresh_engine.current_event is None
    assert fresh_engine.history == []
    assert fresh_engine.alerts == []


# ── Pause/resume tests ────────────────────────────────────────────────────────

@pytest.mark.ml_artifacts
def test_pause_sets_paused_state(fresh_engine):
    fresh_engine.start()
    fresh_engine.pause()
    assert fresh_engine.state == SimulationState.PAUSED


@pytest.mark.ml_artifacts
def test_resume_from_paused(fresh_engine):
    fresh_engine.start()
    fresh_engine.pause()
    fresh_engine.resume()
    assert fresh_engine.state == SimulationState.RUNNING


# ── End-of-dataset ────────────────────────────────────────────────────────────

def test_end_of_dataset_raises_index_error(fresh_engine):
    """When all rows are exhausted, step() raises IndexError."""
    row = _make_mock_row()
    _start_engine_with_mock_rows(fresh_engine, [row])

    mock_result = _mock_assess_result()
    with patch("ml.assessment.assess_machine", return_value=mock_result):
        fresh_engine.step()  # consumes the only row
        with pytest.raises(IndexError):
            fresh_engine.step()


def test_finished_state_after_last_row(fresh_engine):
    """State becomes FINISHED after the last row is consumed."""
    row = _make_mock_row()
    _start_engine_with_mock_rows(fresh_engine, [row])

    mock_result = _mock_assess_result()
    with patch("ml.assessment.assess_machine", return_value=mock_result):
        fresh_engine.step()

    assert fresh_engine.state == SimulationState.FINISHED


# ── Alert generation tests ────────────────────────────────────────────────────

def test_alert_on_critical_transition(fresh_engine):
    """Entering CRITICAL risk level generates a RISK_CRITICAL alert."""
    rows = [_make_mock_row(), _make_mock_row()]
    _start_engine_with_mock_rows(fresh_engine, rows)

    normal = _mock_assess_result(risk_level="NORMAL")
    critical = _mock_assess_result(risk_level="CRITICAL", risk_score=0.85, failure_prob=0.9)

    with patch("ml.assessment.assess_machine", side_effect=[normal, critical]):
        fresh_engine.step()  # NORMAL — no alert
        fresh_engine.step()  # CRITICAL — should generate alert

    alert_types = [a.alert_type for a in fresh_engine.alerts]
    assert "RISK_CRITICAL" in alert_types


def test_alert_on_anomaly_transition(fresh_engine):
    """Anomaly False → True transition generates an ANOMALY alert."""
    rows = [_make_mock_row(), _make_mock_row()]
    _start_engine_with_mock_rows(fresh_engine, rows)

    normal = _mock_assess_result(is_anomaly=False)
    anomalous = _mock_assess_result(is_anomaly=True, anomaly_score=0.7)

    with patch("ml.assessment.assess_machine", side_effect=[normal, anomalous]):
        fresh_engine.step()  # not anomaly
        fresh_engine.step()  # becomes anomaly

    alert_types = [a.alert_type for a in fresh_engine.alerts]
    assert "ANOMALY" in alert_types


def test_alert_on_failure_threshold_crossing(fresh_engine):
    """predicted_failure 0 → 1 generates a FAILURE_THRESHOLD alert."""
    rows = [_make_mock_row(), _make_mock_row()]
    _start_engine_with_mock_rows(fresh_engine, rows)

    not_failed = _mock_assess_result(predicted_failure=0, failure_prob=0.3)
    failed = _mock_assess_result(predicted_failure=1, failure_prob=0.8)

    with patch("ml.assessment.assess_machine", side_effect=[not_failed, failed]):
        fresh_engine.step()
        fresh_engine.step()

    alert_types = [a.alert_type for a in fresh_engine.alerts]
    assert "FAILURE_THRESHOLD" in alert_types


def test_no_duplicate_alert_for_same_risk_level(fresh_engine):
    """If risk stays CRITICAL across steps, only one RISK_CRITICAL alert is generated."""
    rows = [_make_mock_row(), _make_mock_row(), _make_mock_row()]
    _start_engine_with_mock_rows(fresh_engine, rows)

    critical = _mock_assess_result(risk_level="CRITICAL", risk_score=0.85)

    with patch("ml.assessment.assess_machine", return_value=critical):
        for _ in range(3):
            fresh_engine.step()

    critical_alerts = [a for a in fresh_engine.alerts if a.alert_type == "RISK_CRITICAL"]
    assert len(critical_alerts) == 1


# ── Status dict ───────────────────────────────────────────────────────────────

def test_status_dict_has_required_keys(fresh_engine):
    """status() returns a dict with all required top-level keys."""
    status = fresh_engine.status()
    for key in ("state", "speed", "current_step", "total_steps", "current_event", "recent_alerts", "dataset_error"):
        assert key in status, f"Missing key: {key}"


def test_status_initial_values(fresh_engine):
    status = fresh_engine.status()
    assert status["state"] == "idle"
    assert status["current_step"] == 0
    assert status["current_event"] is None
    assert status["recent_alerts"] == []
