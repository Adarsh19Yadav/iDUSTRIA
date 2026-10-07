# Dataset & Data Pipeline

> Phase 2 documentation — INDUSTRIA-X

---

## ⚠️ Synthetic Data Disclaimer

The AI4I 2020 Predictive Maintenance Dataset is a **synthetic** dataset created by researchers for machine learning research purposes.

**It does NOT represent real factory telemetry.**  
Do NOT present statistics derived from this dataset as measurements from real industrial equipment, production lines, or machinery.

---

## Dataset Source

| Field | Value |
|---|---|
| Name | AI4I 2020 Predictive Maintenance Dataset |
| Source | UCI Machine Learning Repository |
| URL | https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset |
| Authors | S. Matzka |
| Licence | CC BY 4.0 |
| Nature | **Synthetic** — not real factory data |

### Citation

> Matzka, S. (2020). AI4I 2020 Predictive Maintenance Dataset. UCI Machine Learning Repository. https://doi.org/10.24432/C5HS5C

---

## Dataset Description

The dataset simulates industrial equipment sensor readings with a binary machine failure label.

| Property | Measured Value |
|---|---|
| Rows | 10,000 |
| Columns | 14 |
| Missing values | 0 |
| Duplicate rows | 0 |
| Failures (target = 1) | 339 (3.39%) |
| No failures (target = 0) | 9,661 (96.61%) |
| Imbalance ratio | ~28.5 : 1 |

> All values above are **measured from the actual dataset**, not assumed.

---

## File Placement

The raw CSV is **not committed** to the repository (binary/large file).

**Required location:** `data/raw/ai4i2020.csv`

**To obtain the file:**

1. Visit https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset
2. Download `ai4i2020.csv`
3. Place it at `data/raw/ai4i2020.csv` relative to the project root

The pipeline will raise a clear `FileNotFoundError` with instructions if the file is missing.

### Directory Structure

```
data/
├── raw/
│   └── ai4i2020.csv        ← place dataset here (not committed)
├── processed/              ← generated artifacts (not committed)
└── external/               ← any external reference data
```

---

## Column Reference

| Column | Type | Role | Notes |
|---|---|---|---|
| UDI | int | **Excluded** | Sequential identifier — no predictive signal |
| Product ID | str | **Excluded** | Encodes UDI + Type — no additional signal |
| Type | str | **Feature** (categorical) | Product quality variant: L / M / H |
| Air temperature [K] | float | **Feature** (numerical) | Ambient temperature |
| Process temperature [K] | float | **Feature** (numerical) | Equipment process temperature |
| Rotational speed [rpm] | int | **Feature** (numerical) | Motor rotational speed |
| Torque [Nm] | float | **Feature** (numerical) | Applied torque |
| Tool wear [min] | int | **Feature** (numerical) | Cumulative tool usage minutes |
| **Machine failure** | int | **TARGET** | Binary: 0 = no failure, 1 = failure |
| TWF | int | **Excluded** (leakage) | Tool Wear Failure sub-type |
| HDF | int | **Excluded** (leakage) | Heat Dissipation Failure sub-type |
| PWF | int | **Excluded** (leakage) | Power Failure sub-type |
| OSF | int | **Excluded** (leakage) | Overstrain Failure sub-type |
| RNF | int | **Excluded** (leakage) | Random Failure sub-type |

---

## Target Definition

**Target column:** `Machine failure`  
**Type:** Binary integer (0 or 1)  
**Positive class:** 1 = machine failure occurred  
**Negative class:** 0 = no failure

**Measured distribution (actual):**

| Class | Count | Rate |
|---|---|---|
| 0 (no failure) | 9,661 | 96.61% |
| 1 (failure) | 339 | 3.39% |

---

## Excluded Columns & Reasons

### Leaky Failure-Mode Columns

The columns TWF, HDF, PWF, OSF, and RNF are **sub-type labels** for the failure event.  
They are only known *because* a failure (`Machine failure = 1`) already occurred.

- When any of these flag columns = 1, `Machine failure` = 1 in **100% of cases**.
- Using them as predictive features would be **target leakage** — the model would trivially achieve near-perfect accuracy during training but fail completely at inference time (when a real failure has not yet occurred).

**Decision:** All five failure-mode flag columns are permanently excluded from the feature set.

### Identifier Columns

| Column | Reason |
|---|---|
| UDI | Sequential integer row ID. Contains no signal about the physical state of equipment. |
| Product ID | Alphanumeric string that encodes UDI (order) + Type (quality variant). The Type information is already captured separately. Including this column would add high-cardinality string noise with no additional predictive value. |

---

## Feature Groups

### Numerical Features (5)

StandardScaler applied (zero mean, unit variance):

| Feature | Min | Max | Mean | Std |
|---|---|---|---|---|
| Air temperature [K] | 295.30 | 304.50 | 300.00 | 2.00 |
| Process temperature [K] | 305.70 | 313.80 | 310.01 | 1.48 |
| Rotational speed [rpm] | 1168 | 2886 | 1538.8 | 179.3 |
| Torque [Nm] | 3.80 | 76.60 | 39.99 | 9.97 |
| Tool wear [min] | 0 | 253 | 107.95 | 63.65 |

> Statistics are **measured from the actual dataset**.

### Categorical Features (1)

OrdinalEncoder applied with explicit ordering L=0, M=1, H=2:

| Feature | Values | Encoding |
|---|---|---|
| Type | L (6,000 rows), M (2,997 rows), H (1,003 rows) | L→0, M→1, H→2 |

> Counts are **measured from the actual dataset**.

---

## Preprocessing Approach

**Design decisions (not assumptions):**

1. **StandardScaler for numerical features** — applied within a sklearn Pipeline so that the scaler is fitted only on the training set. Test-set scaling uses training-set statistics only.
2. **OrdinalEncoder for Type** — the quality levels L < M < H have a natural ordering, making ordinal encoding semantically appropriate and compact. One-hot encoding can be substituted in Phase 3 if ablation results favour it.
3. **ColumnTransformer** — keeps numerical and categorical transformations independent and produces a consistent output column ordering.
4. **`remainder="drop"`** — any column not in NUMERICAL_FEATURES or CATEGORICAL_FEATURES is silently excluded. This provides a safety net for extra columns.

**Module:** `ml/data/features.py` — `build_preprocessor()`

---

## Train/Test Split

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

> Split sizes and failure rates are **measured results** from `ml.data.splitting.make_split`.

**Rationale:**

- **Stratified split** ensures the 3.39% positive-class rate is preserved in both partitions, preventing evaluation bias.
- **Random state 42** is fixed so every Phase 3 training run uses identical data.
- **80/20** gives 2,000 test rows — sufficient to evaluate precision/recall at 3.4% positive rate (~68 failures in test).

**Module:** `ml/data/splitting.py` — `SPLIT_CONFIG`, `make_split()`

---

## Data Pipeline Modules

| Module | Description |
|---|---|
| `ml/data/loader.py` | Load raw CSV; validate required columns; provide actionable errors |
| `ml/data/validation.py` | Full quality checks → `ValidationReport` |
| `ml/data/features.py` | Feature/target split; leakage exclusion; `build_preprocessor()` |
| `ml/data/splitting.py` | Reproducible stratified train/test split; `SPLIT_CONFIG` |

---

## EDA

**Notebook:** `ml/notebooks/eda_ai4i2020.ipynb`

Covers:
- Dataset loading and validation
- Target class balance (imbalance 28.5:1)
- Numerical feature distributions (failure vs no-failure)
- Categorical (Type) distribution and failure rate by type
- Feature–failure boxplot analysis
- Temperature delta informational analysis
- Pearson correlation heatmap
- IQR-based outlier inspection
- Failure-mode sub-column leakage review
- Train/test split positive-rate preservation chart
- Preprocessor smoke test

---

## Limitations

1. **Synthetic data** — The AI4I dataset is synthetic. All modelling results apply only within this simulated distribution. Deployment to real equipment requires retraining on real sensor data.
2. **Severe class imbalance** — 3.39% positive rate requires imbalanced-aware training strategies (SMOTE, class weighting, threshold tuning) in Phase 3.
3. **Static dataset** — The dataset has no timestamps or concept-drift properties. Real-world use would require online/streaming learning adaptations.
4. **No domain validation** — The numerical ranges and correlations reflect the synthetic generation process, not physically grounded industrial data.
5. **Ordinal encoding assumption** — Treating Type as L < M < H is a design decision. Tree-based models are unaffected; linear models implicitly assume this ordering is meaningful.
