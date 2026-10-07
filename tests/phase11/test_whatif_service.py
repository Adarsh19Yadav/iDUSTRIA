"""
tests/phase11/test_whatif_service.py
======================================
Phase 11: Targeted unit tests for the what-if analysis service.

Tests cover:
 - Happy path: valid baseline and scenario produce a WhatIfResult
 - Delta calculations are correct
 - Out-of-distribution warning for scenario values outside training range
 - Validation: NaN, infinity, negative values, invalid Type, extreme values
 - Determinism: same inputs → same result
"""

from __future__ import annotations

import math

import pytest

from backend.services.whatif_service import (
    MachineInputs,
    WhatIfResult,
    _check_out_of_distribution,
    _validate_inputs,
    run_whatif,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

TYPICAL = MachineInputs(
    air_temp_k=300.0,
    process_temp_k=310.0,
    rotational_speed_rpm=1500.0,
    torque_nm=45.0,
    tool_wear_min=100.0,
    type_="M",
)


# ── Validation tests ──────────────────────────────────────────────────────────


def test_validate_invalid_type_raises():
    bad = MachineInputs(
        air_temp_k=300.0, process_temp_k=310.0,
        rotational_speed_rpm=1500.0, torque_nm=45.0,
        tool_wear_min=100.0, type_="X",
    )
    with pytest.raises(ValueError, match="type"):
        _validate_inputs(bad, "scenario")


def test_validate_nan_raises():
    bad = MachineInputs(
        air_temp_k=float("nan"), process_temp_k=310.0,
        rotational_speed_rpm=1500.0, torque_nm=45.0,
        tool_wear_min=100.0, type_="M",
    )
    with pytest.raises(ValueError, match="NaN"):
        _validate_inputs(bad, "baseline")


def test_validate_infinity_raises():
    bad = MachineInputs(
        air_temp_k=300.0, process_temp_k=float("inf"),
        rotational_speed_rpm=1500.0, torque_nm=45.0,
        tool_wear_min=100.0, type_="M",
    )
    with pytest.raises(ValueError, match="infinity"):
        _validate_inputs(bad, "scenario")


def test_validate_negative_torque_raises():
    bad = MachineInputs(
        air_temp_k=300.0, process_temp_k=310.0,
        rotational_speed_rpm=1500.0, torque_nm=-1.0,
        tool_wear_min=100.0, type_="L",
    )
    with pytest.raises(ValueError, match="non-negative"):
        _validate_inputs(bad, "scenario")


def test_validate_extremely_high_rpm_raises():
    # 2× range width beyond max: range = [1000, 3000], width = 2000, extreme = 3000 + 4000 = 7000
    bad = MachineInputs(
        air_temp_k=300.0, process_temp_k=310.0,
        rotational_speed_rpm=8000.0, torque_nm=45.0,
        tool_wear_min=100.0, type_="M",
    )
    with pytest.raises(ValueError, match="extremely"):
        _validate_inputs(bad, "scenario")


def test_validate_typical_inputs_passes():
    """No exception should be raised for typical in-range inputs."""
    _validate_inputs(TYPICAL, "baseline")  # should not raise


# ── OOD detection tests ───────────────────────────────────────────────────────


def test_ood_no_warning_for_typical():
    ood = _check_out_of_distribution(TYPICAL)
    assert ood == []


def test_ood_warning_for_high_tool_wear():
    high_wear = MachineInputs(
        air_temp_k=300.0, process_temp_k=310.0,
        rotational_speed_rpm=1500.0, torque_nm=45.0,
        tool_wear_min=310.0,  # outside [0, 300]
        type_="M",
    )
    ood = _check_out_of_distribution(high_wear)
    assert "tool_wear_min" in ood


def test_ood_warning_for_low_air_temp():
    low_temp = MachineInputs(
        air_temp_k=290.0,  # outside [295, 305]
        process_temp_k=310.0,
        rotational_speed_rpm=1500.0, torque_nm=45.0,
        tool_wear_min=100.0, type_="H",
    )
    ood = _check_out_of_distribution(low_temp)
    assert "air_temp_k" in ood


# ── Integration tests (require ML artifacts) ──────────────────────────────────


@pytest.mark.ml_artifacts
def test_run_whatif_same_inputs_zero_delta():
    """Baseline == scenario → all deltas should be 0."""
    result: WhatIfResult = run_whatif(TYPICAL, TYPICAL)
    assert result.failure_probability_delta == pytest.approx(0.0, abs=1e-6)
    assert result.anomaly_score_delta == pytest.approx(0.0, abs=1e-6)
    assert result.risk_score_delta == pytest.approx(0.0, abs=1e-6)
    assert result.risk_level_changed is False
    assert result.out_of_distribution_warning is None


@pytest.mark.ml_artifacts
def test_run_whatif_deterministic():
    """Same inputs must produce the same result on repeated calls."""
    r1 = run_whatif(TYPICAL, TYPICAL)
    r2 = run_whatif(TYPICAL, TYPICAL)
    assert r1.failure_probability_delta == r2.failure_probability_delta
    assert r1.risk_score_delta == r2.risk_score_delta


@pytest.mark.ml_artifacts
def test_run_whatif_ood_warning_emitted():
    """Scenario with out-of-range tool wear should include OOD warning."""
    high_wear_scenario = MachineInputs(
        air_temp_k=300.0, process_temp_k=310.0,
        rotational_speed_rpm=1500.0, torque_nm=45.0,
        tool_wear_min=310.0, type_="M",
    )
    result = run_whatif(TYPICAL, high_wear_scenario)
    assert result.out_of_distribution_warning is not None
    assert "tool_wear_min" in result.out_of_distribution_warning


@pytest.mark.ml_artifacts
def test_run_whatif_result_structure():
    """Result should have all expected fields with values in [0, 1] where applicable."""
    result = run_whatif(TYPICAL, TYPICAL)
    assert 0.0 <= result.baseline.failure_probability <= 1.0
    assert 0.0 <= result.baseline.anomaly_score <= 1.0
    assert 0.0 <= result.baseline.risk_score <= 1.0
    assert result.baseline.risk_level in {"NORMAL", "WARNING", "CRITICAL"}
