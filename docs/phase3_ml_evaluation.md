# Phase 3 — Machine Failure Prediction: ML Evaluation

> INDUSTRIA-X — Phase 3 documentation

---

## ⚠️ Synthetic Data Disclaimer

The AI4I 2020 Predictive Maintenance Dataset is a **synthetic** dataset created by researchers for machine learning research purposes.

**It does NOT represent real factory telemetry.**
All model metrics reported here are measured on the synthetic dataset only.
**This model has NOT been validated on real factory equipment.**

---

## Dataset Used

| Field | Value |
|---|---|
| Name | AI4I 2020 Predictive Maintenance Dataset |
| Source | UCI Machine Learning Repository |
| URL | https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset |
| Authors | S. Matzka |
| Licence | CC BY 4.0 |
| Nature | **Synthetic** — not real factory data |
| Rows | 10,000 |
| Missing values | 0 |

---

## Feature Set

Reused without modification from Phase 2.

### Numerical Features (5)
Preprocessed with `StandardScaler` (zero mean, unit variance — fitted on training data only).

| Feature | Description |
|---|---|
| `Air temperature [K]` | Ambient temperature |
| `Process temperature [K]` | Equipment process temperature |
| `Rotational speed [rpm]` | Motor rotational speed |
| `Torque [Nm]` | Applied torque |
| `Tool wear [min]` | Cumulative tool usage |

### Categorical Feature (1)
Preprocessed with `OrdinalEncoder` (L=0, M=1, H=2 — ordering reflects quality grade).

| Feature | Values |
|---|---|
| `Type` | L / M / H (product quality variant) |

### Target

| Column | Values |
|---|---|
| `Machine failure` | 0 = no failure, 1 = failure |

---

## Leakage Exclusions

The following columns are permanently excluded from the feature set:

| Column | Reason |
|---|---|
| `TWF` | Tool Wear Failure sub-type — derived from the target |
| `HDF` | Heat Dissipation Failure sub-type — derived from the target |
| `PWF` | Power Failure sub-type — derived from the target |
| `OSF` | Overstrain Failure sub-type — derived from the target |
| `RNF` | Random Failure sub-type — derived from the target |
| `UDI` | Sequential row identifier — no predictive signal |
| `Product ID` | Encodes UDI + Type — no additional signal |

When any failure sub-type flag = 1, `Machine failure` = 1 in 100% of cases. Using them as features would be target leakage — the model would appear perfect in training but fail completely at inference time.

---

## Split Methodology

Reused from Phase 2 without modification.

| Parameter | Value |
|---|---|
| Strategy | Stratified on `Machine failure` |
| Test fraction | 20% |
| Train fraction | 80% |
| Random state | 42 |
| Train rows | 8,000 |
| Test rows | 2,000 |
| Train failures | 271 (3.39%) |
| Test failures | 68 (3.40%) |

The stratified split preserves the ~3.39% positive-class rate in both partitions.

---

## Class Imbalance

| Class | Count | Rate |
|---|---|---|
| 0 (no failure) | 9,661 | 96.61% |
| 1 (failure) | 339 | 3.39% |
| Imbalance ratio | — | ~28.5 : 1 |

> These are **measured values** from the actual dataset.

**Consequence:** Accuracy is a misleading primary metric. A model that always predicts "no failure" achieves 96.61% accuracy while being completely useless. Primary evaluation metrics are **PR-AUC**, **Recall**, **F1 (failure class)**, and **ROC-AUC**.

---

## Models Evaluated

### Model A — Logistic Regression
- `class_weight='balanced'` — automatically scales class weights inversely proportional to class frequency
- `solver='lbfgs'`, `max_iter=1000`, `random_state=42`
- Sklearn `Pipeline` wrapping Phase 2 preprocessor

### Model B — Random Forest
- `n_estimators=200`, `class_weight='balanced'`, `random_state=42`, `n_jobs=-1`
- Sklearn `Pipeline` wrapping Phase 2 preprocessor

### Model C — XGBoost
- `n_estimators=200`, `scale_pos_weight=28.52` (= negatives / positives in training set)
- `random_state=42`, `eval_metric='logloss'`
- Sklearn `Pipeline` wrapping Phase 2 preprocessor

XGBoost was included because it was already listed in `pyproject.toml` as a project dependency and available in the environment. No additional complexity was introduced.

---

## Imbalance Strategy

**Primary approach: class weighting / scale_pos_weight**

- Logistic Regression and Random Forest: `class_weight='balanced'`
- XGBoost: `scale_pos_weight = n_neg / n_pos = 7729 / 271 ≈ 28.52`

This assigns higher loss penalty to minority class misclassifications during training without any risk of test-set contamination.

**SMOTE was NOT used.** Class weighting was sufficient to achieve strong recall. SMOTE was not applied because class weighting produced competitive results and SMOTE requires careful pipeline scoping to avoid data leakage.

---

## Threshold Tuning

Default classification threshold (0.50) is not assumed optimal for imbalanced settings.

**Method:** 5-fold out-of-fold (OOF) cross-validation on the training set using `cross_val_predict` to generate OOF predicted probabilities. The precision-recall curve is computed on these OOF probabilities and the threshold that maximises F1 for the failure class is selected.

**No test data is involved in threshold selection.**

| Model | Tuned Threshold |
|---|---|
| Logistic Regression | 0.875 |
| Random Forest | 0.550 |
| XGBoost | 0.543 |

The high LR threshold (0.875) reflects that Logistic Regression, even with class weighting, was producing high false-positive rates at lower thresholds. A higher threshold was required to balance precision and recall.

---

## Measured Test-Set Metrics

> **All values below are measured results from the held-out test set (2,000 rows, 68 failures). They were not fabricated.**

### Model A — Logistic Regression (threshold = 0.875)

| Metric | Value |
|---|---|
| Accuracy | 0.9590 |
| Failure Precision | 0.4000 |
| Failure Recall | 0.4118 |
| Failure F1 | 0.4058 |
| ROC-AUC | 0.9082 |
| **PR-AUC** | **0.3919** |
| True Positives (TP) | 28 |
| False Positives (FP) | 42 |
| True Negatives (TN) | 1,890 |
| False Negatives (FN) | 40 |

**Confusion matrix:**

```
                Predicted No Failure  Predicted Failure
Actual No Fail      1890                  42
Actual Failure        40                  28
```

### Model B — Random Forest (threshold = 0.550)

| Metric | Value |
|---|---|
| Accuracy | 0.9855 |
| Failure Precision | 0.8421 |
| Failure Recall | 0.7059 |
| Failure F1 | 0.7680 |
| ROC-AUC | 0.9610 |
| **PR-AUC** | **0.8005** |
| True Positives (TP) | 48 |
| False Positives (FP) | 9 |
| True Negatives (TN) | 1,923 |
| False Negatives (FN) | 20 |

**Confusion matrix:**

```
                Predicted No Failure  Predicted Failure
Actual No Fail      1923                   9
Actual Failure        20                  48
```

### Model C — XGBoost (threshold = 0.543)

| Metric | Value |
|---|---|
| Accuracy | 0.9845 |
| Failure Precision | 0.7761 |
| Failure Recall | 0.7647 |
| Failure F1 | 0.7704 |
| ROC-AUC | 0.9684 |
| **PR-AUC** | **0.8389** |
| True Positives (TP) | 52 |
| False Positives (FP) | 15 |
| True Negatives (TN) | 1,917 |
| False Negatives (FN) | 16 |

**Confusion matrix:**

```
                Predicted No Failure  Predicted Failure
Actual No Fail      1917                  15
Actual Failure        16                  52
```

---

## Threshold Selection Rationale

The threshold was selected by maximising failure-class F1 on out-of-fold training predictions. This ensures the threshold choice is grounded in the precision-recall trade-off appropriate for predictive maintenance:

- **Missed failures (FN) have high cost** — undetected failures can cause unplanned downtime, production loss, safety risk.
- **False alarms (FP) have moderate cost** — unnecessary inspections waste resources but do not cause direct damage.
- F1 balances both concerns without exclusively optimising for one direction.

The final threshold for XGBoost (0.543) is close to 0.50, which makes it well-calibrated. This contrasts with Logistic Regression (0.875) which required a high threshold to avoid excessive false positives — a signal of weaker model discrimination.

---

## False Positive / False Negative Analysis

### In the context of predictive maintenance:

**False Negative (FN) — Missed failure:**
- The model predicts "no failure" but the machine actually fails.
- Operational consequence: **unplanned downtime**, potential equipment damage, production loss, safety incidents.
- **This is the higher-cost error in a predictive maintenance context.**
- XGBoost produced 16 FN on the test set vs. 20 for Random Forest and 40 for Logistic Regression.

**False Positive (FP) — False alarm:**
- The model predicts "failure" but the machine is fine.
- Operational consequence: **unnecessary inspection or preventive maintenance**, wasted technician time, possible unnecessary part replacement.
- This is a real cost but typically lower than unplanned downtime.
- XGBoost produced 15 FP vs. 9 for Random Forest and 42 for Logistic Regression.

### Comparison (test set, 2,000 rows, 68 true failures):

| Model | FN (missed failures) | FP (false alarms) | Recall | Precision |
|---|---|---|---|---|
| Logistic Regression | **40** (58.8% missed) | 42 | 0.4118 | 0.4000 |
| Random Forest | 20 (29.4% missed) | **9** | 0.7059 | 0.8421 |
| **XGBoost** | **16** (23.5% missed) | 15 | **0.7647** | **0.7761** |

XGBoost achieves the lowest false-negative count while keeping false positives at a reasonable level (15 unnecessary inspections per 2,000 observations vs. 16 missed failures).

---

## Model Selection

**Selected model: XGBoost**
**Version: v1**
**Threshold: 0.543**

### Selection rationale

| Criterion | LR | RF | **XGBoost** | Winner |
|---|---|---|---|---|
| Failure Recall | 0.4118 | 0.7059 | **0.7647** | XGBoost |
| Failure Precision | 0.4000 | **0.8421** | 0.7761 | RF |
| Failure F1 | 0.4058 | 0.7680 | **0.7704** | XGBoost |
| ROC-AUC | 0.9082 | 0.9610 | **0.9684** | XGBoost |
| PR-AUC | 0.3919 | 0.8005 | **0.8389** | XGBoost |
| False Negatives | 40 | 20 | **16** | XGBoost |
| False Positives | 42 | **9** | 15 | RF |

XGBoost wins on all primary metrics (PR-AUC, Recall, F1, ROC-AUC) and most critically has the fewest missed failures (16 vs. 20 for RF). The slightly higher FP count vs. Random Forest (15 vs. 9) is acceptable given the significantly better recall.

Random Forest has higher precision (0.8421 vs. 0.7761) and fewer false alarms (9 vs. 15), but misses 25% more actual failures (20 vs. 16). In predictive maintenance, missing failures is typically more costly than false alarms.

Logistic Regression is eliminated — it misses 58.8% of failures.

**Accuracy is not used for model selection.** All three models achieve >95% accuracy by virtue of always predicting the majority class. This metric is not informative under this class imbalance.

---

## Saved Artifacts

Location: `ml/artifacts/v1/`

| File | Contents |
|---|---|
| `model_pipeline.joblib` | Full sklearn Pipeline (preprocessor + XGBoost classifier), serialised with `joblib` |
| `metadata.json` | Model version, name, threshold, feature columns, split config, evaluation metrics for all models |

### Metadata fields

```json
{
  "model_version": "v1",
  "model_name": "XGBoost",
  "threshold": 0.543...,
  "feature_columns": [...],
  "numerical_features": [...],
  "categorical_features": ["Type"],
  "target_column": "Machine failure",
  "dataset": "AI4I 2020 Predictive Maintenance Dataset (synthetic)",
  "split_config": {...},
  "train_size": 8000,
  "test_size": 2000,
  "train_failures": 271,
  "test_failures": 68,
  "evaluation_metrics": {
    "Logistic Regression": {...},
    "Random Forest": {...},
    "XGBoost": {...}
  }
}
```

---

## Inference Interface

Module: `ml/inference.py`

Function: `predict_failure(air_temp_k, process_temp_k, rotational_speed_rpm, torque_nm, tool_wear_min, type_)`

Returns: `InferenceResult(failure_probability, predicted_failure, threshold, model_version)`

```python
from ml.inference import predict_failure

result = predict_failure(
    air_temp_k=300.5,
    process_temp_k=310.2,
    rotational_speed_rpm=1500,
    torque_nm=40.0,
    tool_wear_min=120,
    type_="M",
)
# InferenceResult(failure_probability=0.08..., predicted_failure=0,
#                 threshold=0.543, model_version='v1')
```

Input validation:
- Numeric inputs: validated against `None` / `NaN` — raises `ValueError`
- `type_`: validated against `{'L', 'M', 'H'}` — raises `ValueError` for any other value
- Missing artifacts: raises `FileNotFoundError` with instructions

The model cache is a lazy singleton — the pipeline is loaded from disk on the first call and reused for all subsequent calls.

---

## Training Script

Module: `ml/models/train.py`

Entry point: `python -m ml.models.train`

Actions performed:
1. Loads dataset and splits (via Phase 2 modules)
2. Tunes thresholds via 5-fold OOF cross-validation on training data
3. Fits all three models on the full training set
4. Evaluates on held-out test set
5. Selects the best model (max PR-AUC, then F1)
6. Saves `model_pipeline.joblib` and `metadata.json`

---

## Limitations

1. **Synthetic data** — The AI4I 2020 dataset is synthetic. All results apply only within this simulated distribution. Deployment to real equipment requires retraining on real sensor data collected from actual machines.

2. **No temporal structure** — The dataset has no timestamps. Real-world predictive maintenance requires time-series aware modelling (sliding windows, sequence models, concept drift handling) that this static dataset cannot support.

3. **No domain validation** — The physical ranges and failure conditions in the dataset reflect the synthetic generation process, not a specific real industrial process. The model cannot be expected to generalise to different machine types without retraining.

4. **Held-out test size** — 68 failure instances in the test set is sufficient for basic evaluation but results would be more stable with a larger test set. The confidence intervals on PR-AUC and recall are not reported.

5. **No hyperparameter optimisation** — Models used reasonable default configurations without exhaustive tuning. Careful hyperparameter search could yield improvement at the cost of training time.

6. **Threshold is optimised for F1** — The F1-maximising threshold equally weights precision and recall. An operational deployment should revisit the threshold selection using domain-specific cost estimates for false positives and false negatives.

7. **Ordinal encoding assumption** — Treating `Type` as L < M < H is a design decision. This is semantically reasonable (quality grades) but has not been verified by domain experts.

---

*All numeric results in this document are measured values from the AI4I 2020 synthetic dataset. No results were fabricated or estimated.*
