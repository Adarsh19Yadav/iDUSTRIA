"""
tests/phase11/test_maintenance_service.py
==========================================
Phase 11: Targeted unit tests for the maintenance prioritization service.

Tests cover:
 - Priority score formula correctness
 - Ranking order: CRITICAL before WARNING before NORMAL
 - Empty input returns empty list
 - Priority score respects configured weights
 - Invalid inputs raise ValueError
 - Determinism: same list → same ranks
"""

from __future__ import annotations

import pytest

from backend.services.maintenance_service import (
    MachinePriorityInput,
    compute_priority_score,
    rank_machines,
)


# ── compute_priority_score tests ──────────────────────────────────────────────


def test_priority_score_formula():
    """Score = 0.50×risk + 0.30×failure_prob + 0.20×anomaly."""
    score = compute_priority_score(
        risk_score=1.0,
        failure_probability=1.0,
        anomaly_score=1.0,
    )
    assert score == pytest.approx(1.0, abs=1e-6)


def test_priority_score_zero_inputs():
    score = compute_priority_score(
        risk_score=0.0,
        failure_probability=0.0,
        anomaly_score=0.0,
    )
    assert score == pytest.approx(0.0, abs=1e-6)


def test_priority_score_partial():
    """Verify arithmetic: 0.50×0.6 + 0.30×0.4 + 0.20×0.2 = 0.30 + 0.12 + 0.04 = 0.46"""
    score = compute_priority_score(
        risk_score=0.6,
        failure_probability=0.4,
        anomaly_score=0.2,
    )
    assert score == pytest.approx(0.46, abs=1e-6)


def test_priority_score_out_of_range_raises():
    with pytest.raises(ValueError, match="risk_score"):
        compute_priority_score(
            risk_score=1.5,  # > 1.0
            failure_probability=0.5,
            anomaly_score=0.5,
        )


def test_priority_score_negative_raises():
    with pytest.raises(ValueError, match="failure_probability"):
        compute_priority_score(
            risk_score=0.5,
            failure_probability=-0.1,
            anomaly_score=0.5,
        )


# ── rank_machines tests ───────────────────────────────────────────────────────


def test_rank_empty_returns_empty():
    assert rank_machines([]) == []


def test_rank_critical_before_warning_before_normal():
    machines = [
        MachinePriorityInput("A", "NORMAL",   risk_score=0.9, failure_probability=0.9, anomaly_score=0.9),
        MachinePriorityInput("B", "CRITICAL",  risk_score=0.1, failure_probability=0.1, anomaly_score=0.1),
        MachinePriorityInput("C", "WARNING",   risk_score=0.5, failure_probability=0.5, anomaly_score=0.5),
    ]
    ranked = rank_machines(machines)
    ids = [r.machine_id for r in ranked]
    # CRITICAL must be first, WARNING second, NORMAL last
    assert ids[0] == "B"
    assert ids[1] == "C"
    assert ids[2] == "A"


def test_rank_same_level_by_priority_score():
    """Within the same risk level, higher priority_score ranks first."""
    machines = [
        MachinePriorityInput("LOW",  "WARNING", risk_score=0.2, failure_probability=0.2, anomaly_score=0.2),
        MachinePriorityInput("HIGH", "WARNING", risk_score=0.8, failure_probability=0.8, anomaly_score=0.8),
    ]
    ranked = rank_machines(machines)
    assert ranked[0].machine_id == "HIGH"
    assert ranked[1].machine_id == "LOW"


def test_rank_assigns_sequential_ranks():
    machines = [
        MachinePriorityInput(i, "NORMAL", risk_score=0.1, failure_probability=0.1, anomaly_score=0.1)
        for i in range(5)
    ]
    ranked = rank_machines(machines)
    ranks = [r.priority_rank for r in ranked]
    assert ranks == [1, 2, 3, 4, 5]


def test_rank_recommended_review_language():
    """CRITICAL machines get 'Recommended for maintenance review' label."""
    machines = [
        MachinePriorityInput("M1", "CRITICAL", risk_score=0.9, failure_probability=0.9, anomaly_score=0.9),
        MachinePriorityInput("M2", "NORMAL",   risk_score=0.1, failure_probability=0.1, anomaly_score=0.1),
    ]
    ranked = rank_machines(machines)
    critical = next(r for r in ranked if r.machine_id == "M1")
    normal = next(r for r in ranked if r.machine_id == "M2")
    assert "Recommended for maintenance review" in critical.recommended_review
    # NORMAL should not use "maintenance review" language
    assert "routine" in normal.recommended_review


def test_rank_deterministic():
    """Same input list produces same ranking on repeated calls."""
    machines = [
        MachinePriorityInput("A", "CRITICAL", risk_score=0.9, failure_probability=0.8, anomaly_score=0.7),
        MachinePriorityInput("B", "WARNING",  risk_score=0.5, failure_probability=0.5, anomaly_score=0.5),
        MachinePriorityInput("C", "NORMAL",   risk_score=0.1, failure_probability=0.1, anomaly_score=0.1),
    ]
    r1 = rank_machines(machines)
    r2 = rank_machines(machines)
    assert [r.machine_id for r in r1] == [r.machine_id for r in r2]
    assert [r.priority_rank for r in r1] == [r.priority_rank for r in r2]
