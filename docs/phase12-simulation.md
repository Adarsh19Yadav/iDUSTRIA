# Phase 12 — Simulated Real-Time Monitoring

> **SIMULATION DISCLOSURE:**  
> This feature simulates sequential machine monitoring using synthetic historical data
> from the UCI AI4I 2020 dataset (Matzka, 2021, CC BY 4.0).  
> **It is not a live industrial sensor connection.**  
> All sensor readings, failure events, and anomaly events are synthetic.

---

## Overview

Phase 12 adds a step-based simulation engine that reads rows from the AI4I 2020
synthetic dataset in order and evaluates each one through the existing INDUSTRIA-X
ML pipeline. The result is a monitoring dashboard that demonstrates how the system
would behave if machine data arrived sequentially over time.

---

## Synthetic Dataset Source

| Property | Value |
|---|---|
| Dataset | UCI AI4I 2020 Predictive Maintenance Dataset |
| Author | S. Matzka |
| Licence | CC BY 4.0 |
| URL | https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset |
| Rows | 10,000 synthetic observations |
| Features | Air temp (K), Process temp (K), RPM, Torque (Nm), Tool wear (min), Type (L/M/H) |
| Location | `data/raw/ai4i2020.csv` |

The dataset was generated algorithmically — it does **not** represent measurements
from real industrial equipment.

---

## Architecture

```
CSV file
  └─► SimulationEngine (in-memory, step-based singleton)
           │
           ├── _load_dataset()       ← ml.data.loader.load_raw()
           ├── step()                ← assess_machine() per row
           ├── pause() / resume()
           ├── reset()
           └── status()
                    │
                    ▼
           Simulation API (FastAPI)
           POST /api/v1/simulation/start
           POST /api/v1/simulation/pause
           POST /api/v1/simulation/reset
           POST /api/v1/simulation/step
           GET  /api/v1/simulation/status
                    │
                    ▼
           Frontend Simulation Dashboard (/simulation)
           - Start / Pause / Step / Reset controls
           - Speed selector: slow (2s) / normal (800ms) / fast (200ms)
           - Current sensor values panel
           - AI assessment panel
           - Alert panel (recent simulation alerts)
           - Event history table (last 20 steps)
           - Progress bar (Step N / total)
```

### In-Memory State

All simulation state is ephemeral — it lives in the Python process memory and is
not persisted to PostgreSQL. This is intentional: writing 10,000 simulation rows
to the database would create unnecessary load for a demonstration feature.

The frontend maintains its own history of received events (last 100 steps).

---

## Step-Based Operation

The simulation does **not** use a server-side background loop. Instead:

1. The frontend calls `POST /api/v1/simulation/step` at a configurable interval.
2. The backend processes exactly one dataset row per request.
3. The response includes the event, updated state, and any new alerts.

This approach is:
- Predictable and easy to debug
- Avoids background thread management
- Lets the frontend control the pacing (speed selector)
- Allows manual single-stepping for demonstration

---

## ML Integration

Each simulated row is evaluated by the existing unmodified ML pipeline:

```python
# ml/assessment.py
result = assess_machine(
    air_temp_k=...,
    process_temp_k=...,
    rotational_speed_rpm=...,
    torque_nm=...,
    tool_wear_min=...,
    type_=...,
)
```

This calls:
1. `ml.inference.predict_failure` — XGBoost failure probability
2. `ml.anomaly_inference.detect_anomaly` — IsolationForest anomaly score
3. `ml.risk.compute_risk_score` — weighted composite risk

No new model is created. No model is retrained. No thresholds are changed.

---

## Alert Logic

Alerts are **deterministic** and generated on state transitions:

| Trigger | Alert Type | Example Message |
|---|---|---|
| risk_level transitions to WARNING | `RISK_WARNING` | Simulation alert: machine entered WARNING risk state (risk score 0.412). |
| risk_level transitions to CRITICAL | `RISK_CRITICAL` | Simulation alert: machine entered CRITICAL risk state (risk score 0.781). |
| is_anomaly transitions False → True | `ANOMALY` | Simulation alert: anomalous operating pattern detected (anomaly score 0.623). |
| predicted_failure transitions 0 → 1 | `FAILURE_THRESHOLD` | Simulation alert: failure probability (61.2%) crossed the model threshold (0.543). Recommended for review. |

All alert text is informational. No alert says "Machine will fail."

---

## Limitations

1. **Not real-time.** This is a sequential playback of historical synthetic data,
   not a live sensor feed.

2. **Singleton state.** The simulation engine is a single in-memory instance per
   process. Multiple concurrent users share the same simulation state.

3. **No persistence.** Simulation history is held in frontend memory and is lost
   on page refresh or reset.

4. **Dataset dependency.** If `data/raw/ai4i2020.csv` is absent, the simulation
   will report a clear error and not generate fabricated fallback data.

5. **Training distribution.** The ML models were trained on this same dataset.
   Simulation results reflect the model's learned patterns, not independent validation.

6. **Speed limits.** At "fast" speed (200ms polling), network latency between
   frontend and backend may limit throughput. This is a demonstration, not a
   production telemetry pipeline.

---

## Difference from Real Industrial Monitoring

| Property | INDUSTRIA-X Simulation | Real Industrial Monitoring |
|---|---|---|
| Data source | AI4I 2020 synthetic CSV | Physical sensors (OPC-UA, MQTT, etc.) |
| Timing | Driven by frontend polling | Driven by sensor sampling rate |
| Data freshness | Historical (2021 dataset) | Live (milliseconds old) |
| Machine existence | Synthetic identifier `SIM-AI4I-001` | Real registered equipment |
| Failure events | Algorithm-generated labels | Actual equipment failures |
| Purpose | Research / demonstration | Production monitoring |
| Safety-critical use | No | Requires certified system |

> This feature is suitable for demonstrating the INDUSTRIA-X platform's capabilities.
> It must **not** be used for safety-critical decisions about real equipment.

---

## Files Created / Modified

| Path | Purpose |
|---|---|
| `backend/services/simulation_service.py` | Step-based simulation engine |
| `backend/api/simulation.py` | FastAPI simulation endpoints |
| `backend/main.py` | Registered simulation router |
| `frontend/src/types/simulation.ts` | TypeScript types |
| `frontend/src/api/simulation.ts` | Frontend API client |
| `frontend/src/pages/SimulationPage.tsx` | Simulation dashboard |
| `frontend/src/App.tsx` | Added /simulation route + nav item |
| `tests/phase12/test_simulation_service.py` | 17 targeted tests |
| `docs/phase12-simulation.md` | This document |
