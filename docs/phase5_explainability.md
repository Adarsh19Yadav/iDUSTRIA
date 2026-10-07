# Phase 5 — Explainable AI with SHAP

## Overview

Phase 5 adds explainability to the Phase 3 XGBoost failure prediction model
using SHAP (SHapley Additive exPlanations).  The system answers:

> "Why did the model predict this machine as high/low failure risk?"

> **SHAP explains how features influenced the model's prediction; it does not
> establish that a feature physically caused machine failure.**

> All models and explanations are based on the AI4I 2020 *synthetic* dataset
> and have not been validated on real industrial machinery.

---

## 1. SHAP Methodology

### Algorithm

**`shap.TreeExplainer`** — the native, exact SHAP algorithm for tree-based models.

TreeExplainer computes exact Shapley values for tree ensembles in polynomial
time using the tree structure directly.  It does not require a background
dataset (uses `feature_perturbation="tree_path_dependent"` by default).

### Why TreeExplainer?

- Exact computation — not an approximation
- No background dataset required
- Direct integration with the XGBoost classifier
- No new model is created; the same trained classifier from Phase 3 is used

### SHAP Value Space

TreeExplainer returns SHAP values in **log-odds space** for XGBoost binary
classification.

For each observation:
```
log_odds = base_value + Σ shap_values[i]
probability = sigmoid(log_odds)
```

where `base_value` is the expected log-odds across the training set.

The reconstructed probability is identical to `pipeline.predict_proba(X)[:, 1]`.

---

## 2. Model Being Explained

| Property | Value |
|---|---|
| Model | XGBoost (`XGBClassifier`) |
| Artifact | `ml/artifacts/v1/model_pipeline.joblib` |
| Version | `v1` |
| Phase | Phase 3 |
| Features | Air temp, Process temp, Rotational speed, Torque, Tool wear, Type |
| Threshold | 0.543 (Phase 3 threshold) |

The sklearn `Pipeline` contains a `ColumnTransformer` preprocessor followed
by the `XGBClassifier`.  For SHAP, the preprocessor and classifier are
accessed separately — the preprocessor transforms the input, and
`TreeExplainer` is applied directly to the XGBoost model.  This preserves
exact correspondence with the production pipeline.

---

## 3. Local Explanations

### Function

```python
from ml.explainer import explain_prediction

result = explain_prediction(
    air_temp_k=303.0,
    process_temp_k=313.0,
    rotational_speed_rpm=1200,
    torque_nm=68.0,
    tool_wear_min=240,
    type_="L",
)
```

### Output (`ExplanationResult`)

| Field | Type | Description |
|---|---|---|
| `failure_probability` | float | Failure probability (identical to `predict_failure()`) |
| `predicted_failure` | int | 0 or 1, based on Phase 3 threshold (0.543) |
| `threshold` | float | Phase 3 classification threshold |
| `model_version` | str | Artifact version |
| `base_value` | float | SHAP expected log-odds (model average) |
| `shap_sum` | float | Sum of all SHAP values for this observation |
| `features` | list | `FeatureContribution` objects, sorted by `\|shap_value\|` desc |
| `summary_text` | str | Human-readable explanation |

### `FeatureContribution` fields

| Field | Type | Description |
|---|---|---|
| `feature` | str | Feature name (e.g. `'Torque [Nm]'`) |
| `value` | float/str | Raw input value (before preprocessing) |
| `shap_value` | float | SHAP value in log-odds space |
| `direction` | str | `increases_failure_risk` / `decreases_failure_risk` / `neutral` |
| `contribution` | float | `abs(shap_value)` — magnitude of influence |

Features are sorted by descending `contribution` (largest absolute SHAP first).

---

## 4. Human-Readable Summary

The `summary_text` field provides a natural-language explanation.

### Example (high-stress observation)

```
Prediction: HIGH failure risk
Failure probability: 1.0000  (threshold: 0.543)

Features that increased the model's predicted failure risk:
  1. Torque [Nm] = 68.0  (SHAP: +8.4595)
  2. Tool wear [min] = 240.0  (SHAP: +5.0808)
  3. Air temperature [K] = 303.0  (SHAP: +1.0771)
  4. Type = L  (SHAP: +0.2501)

Features that reduced the model's predicted failure risk:
  1. Process temperature [K] = 313.0  (SHAP: -2.6423)
  2. Rotational speed [rpm] = 1200.0  (SHAP: -0.3952)

NOTE: SHAP values show how each feature influenced the model's prediction.
They do not establish physical causation.
```

### Wording rules (strictly enforced in code and tests)

The summary **must not** contain causal language.

| Forbidden | Permitted |
|---|---|
| "caused the failure" | "increased the model's predicted failure risk" |
| "led to failure" | "contributed positively to the prediction" |
| "resulted in" | "pushed the prediction toward failure" |
| "is responsible for" | "reduced the model's predicted failure risk" |

These rules are verified by automated tests.

---

## 5. Global Feature Importance

### Method

```python
from ml.explainer import compute_global_importance

gi = compute_global_importance(sample_size=500)
```

Computes mean absolute SHAP values across a random sample of the Phase 3
training partition (same `random_state=42` split).

This provides a dataset-level view of which features are most influential
across the training distribution — not for a single observation.

### Result (actual, from 500-row training sample)

| Rank | Feature | Mean |SHAP| |
|---|---|---|
| 1 | Torque [Nm] | 4.020 |
| 2 | Tool wear [min] | 3.077 |
| 3 | Air temperature [K] | 1.939 |
| 4 | Rotational speed [rpm] | 1.856 |
| 5 | Process temperature [K] | 0.968 |
| 6 | Type | 0.308 |

Torque and Tool wear are the most influential features globally.  Type has
the least global influence (though it may still matter for individual
observations).

### Artifact saved

`ml/artifacts/v1/global_shap_importance.json`

---

## 6. Interpretation of SHAP Values

### Sign

| Value | Meaning |
|---|---|
| Positive | Feature pushed the model's prediction **toward failure** (higher probability) |
| Negative | Feature pushed the model's prediction **away from failure** (lower probability) |
| Zero | Feature had no measurable influence on this prediction |

### Magnitude

Larger absolute SHAP values indicate stronger influence on the model's output
for this observation.

### Space

SHAP values are in **log-odds space**, not in probability space.  A SHAP value
of +1.0 does not mean "+10 % probability".  The probability impact depends on
the location on the sigmoid curve (i.e., larger near 0.5, smaller near 0 or 1).

### Additivity

The prediction can be fully reconstructed:
```
sigmoid(base_value + Σ shap_values) ≈ failure_probability
```

---

## 7. Consistency Guarantees

- The same `model_pipeline.joblib` used by `predict_failure()` is used for
  SHAP explanations.  No second model is created.
- The failure probability reported by `explain_prediction()` is identical to
  the value returned by `predict_failure()` (within floating-point precision).
- Feature names match `FEATURE_COLUMNS` from `ml.data.features`.
- Preprocessing (StandardScaler + OrdinalEncoder) is identical to production.
- Model version is reported in every explanation result.

---

## 8. Limitations

1. **Log-odds SHAP values are not probability increments.** The SHAP values
   are in log-odds space.  A SHAP value of +2.0 for Torque does not mean
   "Torque adds 20 % to the failure probability".

2. **SHAP shows attribution, not causation.** Feature attributions reflect
   statistical patterns learned from the synthetic training data and the
   model's structure.  They do not establish physical causation.
   A feature with a high positive SHAP value may be correlated with failure
   in the training data without being a physical root cause.

3. **Synthetic data only.** The AI4I 2020 dataset is synthetic.
   SHAP attributions may not reflect the behaviour of real industrial machinery.

4. **Global importance is approximate.** The global feature importance is
   computed on a 500-row sample of the training data.  It is a reasonable
   estimate but not exact.

5. **No interaction effects.** The ranked feature list treats each feature
   independently.  SHAP does not by default decompose feature interaction
   effects in this implementation.

6. **One model only.** Phase 5 explains the Phase 3 XGBoost failure model
   only.  The Phase 4 Isolation Forest anomaly detector is not explained
   (unsupervised models have different SHAP semantics).
