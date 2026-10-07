# Phase 4 — Anomaly Detection & Unified Risk Engine

## Overview

Phase 4 adds two capabilities to INDUSTRIA-X:

1. **Unsupervised anomaly detection** — identifies machines whose sensor readings
   fall outside the normal operating envelope learned from training data, even
   when the Phase 3 failure classifier does not predict failure.
2. **Unified machine risk engine** — combines the Phase 3 failure probability
   with Phase 4 anomaly severity into a single, transparent risk score and
   categorical risk level.

> **Anomaly detection identifies unusual operating patterns; it does not prove
> that a machine is failing.**

> **The unified risk score is a prototype decision-support score and is not an
> industrial safety certification.**

---

## 1. Anomaly Detection Method

**Algorithm:** Isolation Forest (scikit-learn `IsolationForest`)

Isolation Forest is an ensemble of random decision trees that isolates
observations by recursively partitioning the feature space along randomly
selected feature/split-point pairs.  Anomalous observations require fewer
splits to isolate and therefore receive lower raw scores from sklearn's
`decision_function`.

### Why Isolation Forest?

- Unsupervised — requires no failure labels
- Efficient on tabular data with mixed feature types
- Low hyperparameter sensitivity
- Available in scikit-learn (no new dependencies)
- Scales linearly with dataset size

---

## 2. Features Used

| Feature | Type | Notes |
|---|---|---|
| Air temperature [K] | Numerical | Sensor reading |
| Process temperature [K] | Numerical | Sensor reading |
| Rotational speed [rpm] | Numerical | Operational parameter |
| Torque [Nm] | Numerical | Operational parameter |
| Tool wear [min] | Numerical | Cumulative wear counter |
| Type | Categorical (L/M/H) | Product quality variant |

These are the same six features used in Phase 3.

---

## 3. Features Excluded

| Column | Reason |
|---|---|
| Machine failure | **TARGET — must not be used for unsupervised training** |
| TWF | Failure sub-type derived from target (leakage) |
| HDF | Failure sub-type derived from target (leakage) |
| PWF | Failure sub-type derived from target (leakage) |
| OSF | Failure sub-type derived from target (leakage) |
| RNF | Failure sub-type derived from target (leakage) |
| UDI | Sequential row identifier — no predictive signal |
| Product ID | Encodes UDI + Type — no additional signal |

The failure labels were not used at any point during anomaly detector training.

---

## 4. Training Methodology

### Data

Dataset: AI4I 2020 Predictive Maintenance Dataset (synthetic, 10,000 rows).

### Split

The **Phase 3 training split is reproduced exactly** (`random_state=42`,
`test_size=0.20`, stratified on `Machine failure`).  The anomaly detector is
fitted only on the 8,000-row training partition.  The 2,000-row test set is
never seen during training.

This mirrors the Phase 3 methodology and ensures that no test-set information
leaks into the detector.

### Preprocessing

The Phase 2 `ColumnTransformer` preprocessor is reused:
- `StandardScaler` for the five numerical features
- `OrdinalEncoder` with explicit category order `['L', 'M', 'H']` for Type

The preprocessor is fitted on `X_train` inside the sklearn `Pipeline` (same
as Phase 3).

### Isolation Forest configuration

| Parameter | Value | Rationale |
|---|---|---|
| `n_estimators` | 100 | Default; sufficient for 8,000 rows |
| `contamination` | 0.05 | Conservative 5 % prior (see §5) |
| `random_state` | 42 | Reproducibility; matches project-wide seed |
| `n_jobs` | -1 | Parallel tree construction |

### Training statistics (actual, from fitted artifact)

| Metric | Value |
|---|---|
| Training rows | 8,000 |
| Train score mean | 0.0965 |
| Train score std | 0.0495 |
| Train score min | −0.1191 |
| Train score max | 0.1739 |
| Anomaly threshold score | ≈ 0.0000 (5th percentile) |

---

## 5. Anomaly Scoring Methodology

### Raw score (`raw_score`)

`pipeline.decision_function(X)` returns sklearn's raw anomaly score:
- **Positive** → observation is in the normal region (hard to isolate)
- **Negative** → observation is anomalous (easy to isolate)
- ≈ 0 → near the decision boundary

The boundary is set internally by sklearn based on the `contamination`
parameter fitted on training data.

### `is_anomaly` flag

```
is_anomaly = True  when  raw_score < 0
```

Equivalently, `pipeline.predict(X) == -1`.  This is the sklearn-native
boundary.  Approximately 5 % of training observations are expected to be
flagged as anomalies under this setting.

### Normalised `anomaly_score`

The raw score is NOT a probability and is not labelled as one.  To produce
an intuitive severity index in `[0, 1]`, the score is normalised using the
training distribution stored in `anomaly_metadata.json`:

```
negated      = −raw_score          # positive = anomalous
min_bound    = −train_score_max    # minimum negated value (most normal training point)
max_bound    = −train_score_min    # maximum negated value (most anomalous training point)

anomaly_score = clip((negated − min_bound) / (max_bound − min_bound), 0, 1)
```

Interpretation:
- `anomaly_score ≈ 0` — observation is firmly in the normal operating range
- `anomaly_score ≈ 1` — observation is as anomalous as the most extreme
  training-set outlier
- Values > 1 are not possible (clipped); values from new data outside the
  training range are clipped at 1.

The `anomaly_score` is a **normalised severity index, not a probability**.

---

## 6. Anomaly Threshold / Contamination

**Method:** contamination-based threshold on training data.

**Contamination:** `0.05` (5 %)

**Threshold score:** `≈ 0.0` (5th percentile of training `decision_function` scores)

### Rationale

- The contamination rate is **not tuned against the failure label**.  It is a
  prior assumption about what fraction of operating conditions may be unusual.
- 5 % is a conservative value that avoids over-alerting while still catching
  genuine operational anomalies.
- The dataset's actual failure rate is ~3.4 %.  Setting contamination slightly
  higher than the failure rate ensures the detector is sensitive to unusual
  patterns that may not (yet) manifest as failures.
- The threshold (≈ 0) is derived directly from the training distribution by
  sklearn's `contamination` mechanism.  It is stable and reproducible.

---

## 7. Unified Risk Formula

```
risk_score = w_failure × failure_probability
           + w_anomaly  × anomaly_score
```

**Default weights:**

| Component | Weight | Rationale |
|---|---|---|
| `failure_probability` | 0.70 | Calibrated ML signal from Phase 3 XGBoost |
| `anomaly_score` | 0.30 | Unsupervised severity index |

The failure probability receives a higher weight because it is a calibrated
output from a supervised model trained and threshold-tuned on the same domain.
The anomaly score supplements it by adding sensitivity to unusual patterns
that the failure classifier may not flag.

**Weights are configurable** via `compute_risk_score(w_failure=..., w_anomaly=...)`.
Weights must sum to 1.0.

### Machine criticality

The `machine_criticality` parameter (float in `[0, 1]`) is accepted and
stored in the assessment result for traceability.  It is **not currently
applied to the formula** because the AI4I 2020 dataset does not include
machine-criticality ratings.  The default value is `1.0` (most critical) as a
safe-side conservative choice.

---

## 8. Risk Thresholds

| Level | Condition | Interpretation |
|---|---|---|
| `NORMAL` | `risk_score < 0.40` | No immediate action required |
| `WARNING` | `0.40 ≤ risk_score < 0.70` | Monitor closely; investigate if sustained |
| `CRITICAL` | `risk_score ≥ 0.70` | Prompt inspection recommended |

Thresholds are configurable via `compute_risk_score(warning_threshold=..., critical_threshold=...)`.

These levels are **decision-support categories for this prototype system**.
They are not certified industrial safety classifications.

---

## 9. Combined Assessment Interface

### Function

```python
from ml.assessment import assess_machine

result = assess_machine(
    air_temp_k=300.5,
    process_temp_k=310.2,
    rotational_speed_rpm=1500,
    torque_nm=40.0,
    tool_wear_min=120,
    type_="M",
)
```

### Output (`AssessmentResult`)

| Field | Type | Description |
|---|---|---|
| `failure_probability` | float [0, 1] | Phase 3 XGBoost failure probability |
| `predicted_failure` | int {0, 1} | Threshold-applied failure class (threshold = 0.543) |
| `anomaly_score` | float [0, 1] | Normalised anomaly severity (not a probability) |
| `is_anomaly` | bool | True if IsolationForest classifies observation as outlier |
| `risk_score` | float [0, 1] | Weighted composite risk score |
| `risk_level` | str | NORMAL / WARNING / CRITICAL |
| `failure_threshold` | float | Phase 3 classification threshold used |
| `model_version` | str | Failure model artifact version |
| `anomaly_version` | str | Anomaly detector artifact version |
| `machine_criticality` | float | Criticality value provided (stored for traceability) |

The function raises `ValueError` for invalid inputs and `FileNotFoundError`
when artifacts are missing.  It never silently returns fabricated values.

---

## 10. Artifact Versions

| Artifact | Path | Description |
|---|---|---|
| `anomaly_pipeline.joblib` | `ml/artifacts/v1/` | Fitted sklearn Pipeline (preprocessor + IsolationForest) |
| `anomaly_metadata.json` | `ml/artifacts/v1/` | Training statistics, hyperparameters, feature list |

Training is reproduced by:

```bash
python -m ml.anomaly_train
```

---

## 11. Limitations

1. **Synthetic data only.** The AI4I 2020 dataset is synthetic and does not
   represent real factory equipment.  Neither the anomaly detector nor the
   risk engine has been validated on real industrial machinery.

2. **Anomaly ≠ failure.** An `is_anomaly=True` flag indicates an unusual
   operating condition relative to the training distribution.  It does not
   prove that the machine is failing or will fail.

3. **Contamination is a prior, not a calibrated rate.** The 5 % contamination
   value is an engineering choice, not an empirically measured anomaly
   prevalence.  Adjust it based on domain knowledge if available.

4. **Risk thresholds are prototype values.** The WARNING/CRITICAL thresholds
   (0.40 / 0.70) are reasonable starting points.  They should be validated
   and tuned against real operational outcomes in a production deployment.

5. **Machine criticality is not data-driven.** The current default of 1.0 is
   a conservative safe-side choice.  Real criticality ratings would require
   separate asset-management data.

6. **No temporal context.** The detector and risk engine operate on individual
   observations.  Trend detection (e.g., rising anomaly scores over time)
   is not implemented in Phase 4.
