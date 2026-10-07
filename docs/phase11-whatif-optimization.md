# Phase 11 — What-If Analysis & Maintenance Prioritization

## Overview

Phase 11 adds two capabilities:

1. **What-If Analysis** — ML-based comparison of baseline vs. modified machine operating conditions
2. **Maintenance Prioritization** — ranked work-order list based on current risk scores

Both are deterministic given the same inputs and ML artifact versions.

## What-If Analysis

### Purpose

Allows operators to simulate the effect of changing operating parameters before committing
to a maintenance or operational change.

> ⚠️ All results are model simulations based on the AI4I 2020 **synthetic** training dataset.
> They represent model-estimated changes, not guaranteed physical outcomes.

### Endpoint

`POST /api/v1/whatif/analyze` — requires `X-API-Key`.

**Request:**

```json
{
  "baseline": {
    "Air temperature [K]": 300.0,
    "Process temperature [K]": 310.0,
    "Rotational speed [rpm]": 1500.0,
    "Torque [Nm]": 45.0,
    "Tool wear [min]": 100.0,
    "Type": "M"
  },
  "scenario": {
    "Air temperature [K]": 305.0,
    "Process temperature [K]": 315.0,
    "Rotational speed [rpm]": 1200.0,
    "Torque [Nm]": 50.0,
    "Tool wear [min]": 200.0,
    "Type": "M"
  }
}
```

**Response includes:**

- `baseline` assessment snapshot (failure_probability, anomaly_score, risk_score, risk_level)
- `scenario` assessment snapshot
- `change` delta values (probability_delta, anomaly_delta, risk_delta, risk_level_changed)
- `out_of_distribution_warning` — flagged if inputs fall outside the training distribution
- `disclaimer` — explicit model-simulation caveat

### Out-of-Distribution Warning

The analysis checks whether inputs fall outside the statistical range observed in the
AI4I 2020 training data. If inputs are OOD, a warning is included in the response.
This is a best-effort heuristic, not a formal distribution test.

### Implementation

| Module | Purpose |
|---|---|
| `backend/api/whatif.py` | FastAPI router and request/response schemas |
| `backend/services/whatif_service.py` | Pipeline: feature engineering → model prediction → delta computation |

## Maintenance Prioritization

### Purpose

Generates a ranked list of machines by urgency, enabling operators to allocate
maintenance resources to highest-risk assets first.

### Endpoint

`POST /api/v1/maintenance/prioritize` — requires `X-API-Key`.

**Request:** list of machine assessments or machine IDs with latest assessment data.

**Response:** ranked machines with risk scores, recommended action priority, and justification.

### Ranking Logic

Machines are ranked by composite risk score (0–100). Risk is a weighted combination of:

- Failure probability (from the ML model)
- Anomaly score (from Isolation Forest)
- Tool wear and operating condition factors

Risk levels:
- `CRITICAL` — risk ≥ threshold (configurable)
- `HIGH` — elevated risk
- `MEDIUM` — moderate risk
- `LOW` — normal operation

### Implementation

| Module | Purpose |
|---|---|
| `backend/api/maintenance.py` | FastAPI router |
| `backend/services/maintenance_service.py` | Prioritization and ranking logic |

## Limitations

1. What-if results are based on the AI4I 2020 synthetic dataset — not real factory data.
2. The ML model was trained on historical patterns; novel operating conditions may not be well-represented.
3. Out-of-distribution detection is heuristic, not statistical.
4. Prioritization rankings reflect model estimates only — human judgment is required before acting.
5. No multi-machine dependency modelling (each machine is assessed independently).
