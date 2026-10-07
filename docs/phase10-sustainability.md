# Phase 10 — Sustainability & Energy Intelligence

## Overview

Phase 10 adds a **Sustainability & Energy Intelligence** module to INDUSTRIA-X.

Because the AI4I 2020 dataset contains **no real electrical energy measurements**, all
energy and carbon outputs are **engineering estimates** derived from the kinematic parameters
already available in the dataset (rotational speed and torque).

All values are clearly labelled as **ESTIMATED / SIMULATED / PROJECTED** and must not be
used for regulatory compliance, energy audits, or financial carbon accounting.

---

## SDG Alignment

| SDG | Relevance |
|-----|-----------|
| **SDG 9 — Industry, Innovation and Infrastructure** | Primary — demonstrates intelligent use of industrial data for operational insight |
| **SDG 13 — Climate Action** | Secondary — provides transparency into machine energy proxies and associated carbon estimates |

---

## Formulas

### 1. Mechanical Power Estimation

Mechanical shaft power is estimated from torque and rotational speed using the standard
kinematic relationship:

```
ω [rad/s]   = 2π × RPM / 60
P_mech [W]  = τ [Nm] × ω [rad/s]
P_mech [kW] = P_mech [W] / 1000
```

**Assumption:** The machine is modelled as a rotating shaft. In a real industrial system,
additional losses (bearings, couplings, gearboxes) would reduce net delivered power.

### 2. Estimated Electrical Input Power

```
P_elec [kW] = P_mech [kW] / η
```

where `η` (eta) is the assumed **drivetrain efficiency** (dimensionless, 0–1).

The default value `η = 0.88` is an illustrative mid-range figure for industrial AC
induction motor drives. This is **not** derived from any measurement of the AI4I machines.

### 3. Estimated Energy Consumption

```
E [kWh] = P_elec [kW] × t [h]
```

where `t` is the configurable operating duration in hours.

### 4. Estimated CO₂ Equivalent

```
CO₂e [kg] = E [kWh] × EF [kg CO₂e / kWh]
```

where `EF` is the **grid emission factor**.

The default `EF = 0.4 kg CO₂e/kWh` is a **generic illustrative value only**.
It does not represent any specific country, grid, or published emission inventory.
Users should substitute a grid-specific emission factor for any meaningful analysis.

---

## Configurable Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `efficiency` | `0.88` | Drivetrain efficiency η (0–1). Represents combined motor + gearbox + coupling losses. |
| `emission_factor_kg_co2e_per_kwh` | `0.4` | Grid carbon intensity in kg CO₂e/kWh. Generic illustrative default. |
| `operating_hours` | `8.0` | Duration of operation in hours (per estimate). |

All three parameters are exposed as optional request body fields in the API and can be
overridden per request.

---

## API

### `POST /api/v1/sustainability/estimate`

Compute estimated power, energy, and CO₂e from machine operating parameters.

**Request body:**

```json
{
  "machine_type": "M",
  "rotational_speed_rpm": 1500,
  "torque_nm": 45,
  "operating_hours": 8,
  "efficiency": 0.88,
  "emission_factor_kg_co2e_per_kwh": 0.4
}
```

**Response (example):**

```json
{
  "machine_type": "M",
  "rotational_speed_rpm": 1500,
  "torque_nm": 45,
  "operating_hours": 8,
  "estimated_mechanical_power_kw": 7.0686,
  "estimated_electrical_power_kw": 8.0325,
  "estimated_energy_kwh": 64.2601,
  "estimated_co2e_kg": 25.7040,
  "assumptions": {
    "efficiency": 0.88,
    "emission_factor_kg_co2e_per_kwh": 0.4,
    "formula_mechanical_power": "P_mech_kW = (torque_nm × 2π × rpm / 60) / 1000",
    "formula_electrical_power": "P_elec_kW = P_mech_kW / efficiency",
    "formula_energy": "E_kwh = P_elec_kW × operating_hours",
    "formula_co2e": "CO2e_kg = E_kwh × emission_factor_kg_co2e_per_kwh",
    "disclaimer": "These values are engineering estimates..."
  }
}
```

### `GET /api/v1/sustainability/insights`

Returns deterministic engineering insights about energy and carbon levers.
No LLM inference. No fabricated statistics.

---

## Files Created / Modified

### New files

| File | Purpose |
|------|---------|
| `backend/services/sustainability_service.py` | Core deterministic calculation functions + Pydantic schemas |
| `backend/api/sustainability.py` | FastAPI router with `/estimate` and `/insights` endpoints |
| `frontend/src/api/sustainability.ts` | Frontend API service |
| `frontend/src/types/sustainability.ts` | TypeScript type definitions |
| `frontend/src/pages/SustainabilityPage.tsx` | Sustainability dashboard page |
| `tests/unit/test_sustainability_service.py` | 13 unit tests for service functions |
| `tests/phase8/test_sustainability_api.py` | 13 API integration tests |
| `docs/phase10-sustainability.md` | This document |

### Modified files

| File | Change |
|------|--------|
| `backend/main.py` | Registered `sustainability_router` |
| `frontend/src/App.tsx` | Replaced ComingSoon with `SustainabilityPage`, updated nav and sidebar footer |

---

## Test Coverage

26 targeted tests added (13 unit + 13 API integration). All pass.

| Test | What it covers |
|------|---------------|
| `test_mechanical_power_known_value` | Formula correctness: P = τω |
| `test_mechanical_power_small_values` | Positive result for small inputs |
| `test_electrical_power_default_efficiency` | Default η = 0.88 |
| `test_electrical_power_custom_efficiency` | Lower η → higher electrical draw |
| `test_energy_kwh_proportional_to_hours` | Doubling hours doubles energy |
| `test_co2e_default_factor` | Default emission factor |
| `test_co2e_custom_emission_factor` | Higher EF → higher CO₂e |
| `test_invalid_rpm_zero` | ValueError on non-positive RPM |
| `test_invalid_torque_negative` | ValueError on negative torque |
| `test_invalid_efficiency_zero` | ValueError on zero efficiency |
| `test_invalid_operating_hours_zero` | ValueError on zero hours |
| `test_full_estimate_structure` | All fields present, disclaimer text present |
| `test_full_estimate_deterministic` | Same inputs → identical outputs |
| API: `test_estimate_success_returns_200` | HTTP 200 for valid input |
| API: `test_estimate_response_structure` | All response fields present |
| API: `test_estimate_assumptions_disclosure` | Disclaimer and config in response |
| API: `test_estimate_values_are_positive` | Positive outputs for valid inputs |
| API: `test_estimate_custom_efficiency` | Efficiency configurable via API |
| API: `test_estimate_custom_emission_factor` | Emission factor configurable |
| API: `test_estimate_invalid_zero_rpm` | 422 on zero RPM |
| API: `test_estimate_invalid_negative_torque` | 422 on negative torque |
| API: `test_estimate_invalid_machine_type` | 422 on invalid machine type |
| API: `test_estimate_with_valid_machine_type` | machine_type echoed correctly |
| API: `test_insights_returns_200` | Insights endpoint reachable |
| API: `test_insights_response_structure` | Insights list + disclaimer present |
| API: `test_insights_disclaimer_present` | Non-empty disclaimer |

---

## Limitations

1. **No real energy measurements.** The AI4I dataset contains only kinematic and temperature
   sensor data. There are no electrical watt-meters, current transducers, or power analysers.
   All energy values are theoretical proxies.

2. **Single-machine, steady-state model.** The formula assumes constant torque and speed over
   the operating period. Real machines operate at varying load profiles.

3. **Efficiency is illustrative.** The default drivetrain efficiency (0.88) is a generic
   engineering value. Actual efficiency depends on motor model, load fraction, temperature,
   age, and condition.

4. **Emission factor is generic.** The default 0.4 kg CO₂e/kWh is illustrative only.
   Real analysis requires a grid-specific emission factor from an authoritative source
   (e.g. national grid operator, IEA country data).

5. **No process-level energy.** Cutting forces, coolant pumps, control electronics, and
   auxiliary loads are not captured.

---

## Future Requirements for Real Energy Intelligence

To replace these estimates with real data, a production deployment would require:

- **Calibrated electrical energy meters** (class 0.5S or better) on each machine supply circuit
- **Real-time power monitoring** at ≥1 Hz sampling rate
- **Site-specific grid emission factor** from a current, authoritative source
- **Load profile recording** rather than steady-state assumptions
- **Integration with MES/SCADA** for production context (parts per kWh, etc.)

---

## Difference: Estimated vs Measured Energy

| | Estimated (this module) | Measured (future) |
|--|------------------------|-------------------|
| Source | Kinematic formula | Electrical meter reading |
| Accuracy | Order-of-magnitude proxy | ±0.5% with calibrated meter |
| Requires hardware? | No | Yes — energy meter |
| Use for compliance? | No | Potentially, if audited |
| Suitable for production optimisation? | Directional guidance only | Yes |

---

*Phase 10 complete — INDUSTRIA-X now provides transparent, deterministic sustainability
estimates aligned with SDG 9 and SDG 13.*
