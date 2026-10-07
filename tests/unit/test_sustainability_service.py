"""
tests/unit/test_sustainability_service.py
=========================================
Phase 10: Targeted unit tests for the sustainability service.

Covers:
 1.  Mechanical power calculation (known formula result)
 2.  Electrical power with default efficiency
 3.  Electrical power with custom efficiency
 4.  Energy calculation
 5.  CO2e calculation with default emission factor
 6.  CO2e calculation with custom emission factor
 7.  Invalid RPM (non-positive)
 8.  Invalid torque (non-positive)
 9.  Invalid efficiency (zero)
10.  Invalid operating hours (zero)
11.  Compute full estimate — structure and labels
12.  Full estimate — deterministic reproducibility
"""

import math
import pytest

from backend.services.sustainability_service import (
    estimate_mechanical_power_kw,
    estimate_electrical_power_kw,
    estimate_energy_kwh,
    estimate_co2e_kg,
    compute_sustainability_estimate,
    DEFAULT_EFFICIENCY,
    DEFAULT_EMISSION_FACTOR_KG_CO2E_PER_KWH,
)


# ── 1. Mechanical power: P = τ × ω, ω = 2π × RPM / 60 ───────────────────────

def test_mechanical_power_known_value():
    """P = 45 Nm × (2π × 1500/60) = 45 × 157.08... = 7068.58... W = 7.068... kW"""
    expected_w = 45.0 * (2 * math.pi * 1500 / 60)
    expected_kw = round(expected_w / 1000.0, 6)
    result = estimate_mechanical_power_kw(1500.0, 45.0)
    assert abs(result - expected_kw) < 1e-5


def test_mechanical_power_small_values():
    """Ensure small but valid inputs produce a positive result."""
    result = estimate_mechanical_power_kw(100.0, 1.0)
    assert result > 0


# ── 2–3. Electrical power ─────────────────────────────────────────────────────

def test_electrical_power_default_efficiency():
    """Electrical power = mechanical / efficiency."""
    mech = estimate_mechanical_power_kw(1500.0, 45.0)
    elec = estimate_electrical_power_kw(mech)
    expected = round(mech / DEFAULT_EFFICIENCY, 6)
    assert abs(elec - expected) < 1e-9


def test_electrical_power_custom_efficiency():
    """Custom efficiency of 0.75 increases estimated electrical draw."""
    mech = estimate_mechanical_power_kw(1500.0, 45.0)
    elec_default = estimate_electrical_power_kw(mech, DEFAULT_EFFICIENCY)
    elec_lower = estimate_electrical_power_kw(mech, 0.75)
    assert elec_lower > elec_default  # lower efficiency → higher electrical input


# ── 4. Energy calculation ─────────────────────────────────────────────────────

def test_energy_kwh_proportional_to_hours():
    """Energy doubles if operating hours double."""
    elec_kw = 8.0
    e8 = estimate_energy_kwh(elec_kw, 8.0)
    e16 = estimate_energy_kwh(elec_kw, 16.0)
    assert abs(e16 - 2 * e8) < 1e-9


# ── 5–6. CO2e ─────────────────────────────────────────────────────────────────

def test_co2e_default_factor():
    energy = 10.0  # kWh
    co2e = estimate_co2e_kg(energy)
    assert abs(co2e - round(energy * DEFAULT_EMISSION_FACTOR_KG_CO2E_PER_KWH, 6)) < 1e-9


def test_co2e_custom_emission_factor():
    """Higher emission factor increases CO2e."""
    energy = 10.0
    co2e_low = estimate_co2e_kg(energy, 0.2)
    co2e_high = estimate_co2e_kg(energy, 0.8)
    assert co2e_high > co2e_low


# ── 7–10. Invalid inputs raise ValueError ─────────────────────────────────────

def test_invalid_rpm_zero():
    with pytest.raises(ValueError, match="rotational_speed_rpm"):
        estimate_mechanical_power_kw(0.0, 45.0)


def test_invalid_torque_negative():
    with pytest.raises(ValueError, match="torque_nm"):
        estimate_mechanical_power_kw(1500.0, -5.0)


def test_invalid_efficiency_zero():
    with pytest.raises(ValueError, match="efficiency"):
        estimate_electrical_power_kw(7.0, 0.0)


def test_invalid_operating_hours_zero():
    with pytest.raises(ValueError, match="operating_hours"):
        estimate_energy_kwh(7.0, 0.0)


# ── 11–12. Full estimate ──────────────────────────────────────────────────────

def test_full_estimate_structure():
    """compute_sustainability_estimate returns a complete SustainabilityEstimate."""
    result = compute_sustainability_estimate(
        rotational_speed_rpm=1500.0,
        torque_nm=45.0,
        operating_hours=8.0,
        machine_type="M",
    )
    assert result.estimated_mechanical_power_kw > 0
    assert result.estimated_electrical_power_kw > result.estimated_mechanical_power_kw
    assert result.estimated_energy_kwh > 0
    assert result.estimated_co2e_kg > 0
    assert result.machine_type == "M"
    # Assumptions are documented
    assert "NOT measured" in result.assumptions.disclaimer
    assert result.assumptions.efficiency == DEFAULT_EFFICIENCY
    assert result.assumptions.emission_factor_kg_co2e_per_kwh == DEFAULT_EMISSION_FACTOR_KG_CO2E_PER_KWH


def test_full_estimate_deterministic():
    """Same inputs must produce identical outputs every time."""
    kwargs = dict(
        rotational_speed_rpm=1200.0,
        torque_nm=30.0,
        operating_hours=4.0,
        machine_type="L",
        efficiency=0.85,
        emission_factor_kg_co2e_per_kwh=0.35,
    )
    r1 = compute_sustainability_estimate(**kwargs)
    r2 = compute_sustainability_estimate(**kwargs)
    assert r1.estimated_mechanical_power_kw == r2.estimated_mechanical_power_kw
    assert r1.estimated_energy_kwh == r2.estimated_energy_kwh
    assert r1.estimated_co2e_kg == r2.estimated_co2e_kg
