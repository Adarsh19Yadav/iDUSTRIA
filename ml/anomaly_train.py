"""ml/anomaly_train.py — Phase 4 Isolation Forest anomaly detector training.

SYNTHETIC DATA NOTICE
---------------------
Trained on the AI4I 2020 *synthetic* dataset.
Results do NOT represent real factory equipment behaviour.

METHOD
------
Isolation Forest is an unsupervised anomaly detection algorithm that isolates
observations by randomly partitioning the feature space.  Anomalous points
require fewer splits to isolate and therefore receive lower (more negative)
raw scores from sklearn's ``decision_function``.

DESIGN DECISIONS
----------------
- Fitted ONLY on X_train (the same 80 % split used in Phase 3, same
  random_state=42) so no test-set information leaks into the detector.
- Failure labels (Machine failure, TWF, HDF, PWF, OSF, RNF) are NOT used.
- contamination=0.05 (5 %) — a conservative prior that roughly 1-in-20
  training observations may be operationally unusual.  This is not tuned
  against the failure label.
- The same Phase 2 ColumnTransformer preprocessor is reused (StandardScaler
  for numerical features, OrdinalEncoder for Type L<M<H).
- The full preprocessing + IsolationForest is wrapped in a single sklearn
  Pipeline and saved as a versioned joblib artifact.

ARTIFACT
--------
  ml/artifacts/v1/anomaly_pipeline.joblib
  ml/artifacts/v1/anomaly_metadata.json

Usage
-----
    python -m ml.anomaly_train
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np

from ml.data.features import get_X_y, build_preprocessor, FEATURE_COLUMNS
from ml.data.loader import load_raw
from ml.data.splitting import make_split, SPLIT_CONFIG

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ANOMALY_VERSION = "v1"
ARTIFACTS_DIR = Path("ml/artifacts") / ANOMALY_VERSION
RANDOM_STATE = SPLIT_CONFIG["random_state"]  # 42 — same as Phase 3

#: Conservative contamination prior: ~5 % of training observations are
#: considered potentially anomalous.  Not tuned against the failure label.
CONTAMINATION = 0.05

#: IsolationForest hyperparameters (no grid search — kept minimal).
N_ESTIMATORS = 100


# ---------------------------------------------------------------------------
# Training routine
# ---------------------------------------------------------------------------


def train_anomaly_detector() -> dict:
    """Fit an Isolation Forest on Phase 3 training data and save the artifact.

    Returns
    -------
    dict
        Metadata dict that is also persisted to anomaly_metadata.json.
    """
    from sklearn.ensemble import IsolationForest
    from sklearn.pipeline import Pipeline

    print("=== INDUSTRIA-X Phase 4 — Anomaly Detector Training ===\n")

    # ------------------------------------------------------------------
    # 1. Load data and reproduce the Phase 3 train split
    # ------------------------------------------------------------------
    print("[1/4] Loading dataset and reproducing Phase 3 train split …")
    df = load_raw()
    X, y = get_X_y(df)  # y is NOT used — unsupervised
    X_train, X_test, y_train, _ = make_split(X, y)

    print(f"      Train rows : {len(X_train)}")
    print(f"      Features   : {FEATURE_COLUMNS}")
    print(f"      Labels used: NO  (unsupervised)")

    # ------------------------------------------------------------------
    # 2. Build pipeline (preprocessor + IsolationForest)
    # ------------------------------------------------------------------
    print("\n[2/4] Building anomaly pipeline …")
    preprocessor = build_preprocessor()
    iso_forest = IsolationForest(
        n_estimators=N_ESTIMATORS,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    anomaly_pipeline = Pipeline(
        [
            ("preprocessor", preprocessor),
            ("detector", iso_forest),
        ]
    )

    # ------------------------------------------------------------------
    # 3. Fit on training data only
    # ------------------------------------------------------------------
    print("[3/4] Fitting IsolationForest on training data only …")
    anomaly_pipeline.fit(X_train)

    # Compute the offset threshold stored by sklearn after fitting
    # (decision_function ≥ 0 → inlier; < 0 → anomaly when using default
    #  contamination-based offset)
    train_scores = anomaly_pipeline.decision_function(X_train)
    threshold_score = float(np.percentile(train_scores, CONTAMINATION * 100))

    print(f"      Train score mean  : {train_scores.mean():.4f}")
    print(f"      Train score std   : {train_scores.std():.4f}")
    print(f"      Train score min   : {train_scores.min():.4f}")
    print(f"      Train score max   : {train_scores.max():.4f}")
    print(f"      Anomaly threshold : {threshold_score:.4f}  "
          f"(= {CONTAMINATION*100:.0f}th percentile of training scores)")

    # ------------------------------------------------------------------
    # 4. Save artifacts
    # ------------------------------------------------------------------
    print("\n[4/4] Saving artifacts …")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    pipeline_path = ARTIFACTS_DIR / "anomaly_pipeline.joblib"
    joblib.dump(anomaly_pipeline, pipeline_path)
    print(f"      Saved: {pipeline_path}")

    metadata = {
        "anomaly_version": ANOMALY_VERSION,
        "algorithm": "IsolationForest",
        "n_estimators": N_ESTIMATORS,
        "contamination": CONTAMINATION,
        "random_state": RANDOM_STATE,
        "feature_columns": FEATURE_COLUMNS,
        "train_rows": int(len(X_train)),
        "labels_used_in_training": False,
        "train_score_mean": float(train_scores.mean()),
        "train_score_std": float(train_scores.std()),
        "train_score_min": float(train_scores.min()),
        "train_score_max": float(train_scores.max()),
        "anomaly_threshold_score": threshold_score,
        "dataset": "AI4I 2020 Predictive Maintenance Dataset (synthetic)",
        "split_config": SPLIT_CONFIG,
    }

    metadata_path = ARTIFACTS_DIR / "anomaly_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"      Saved: {metadata_path}")

    print(f"\n  All anomaly artifacts saved to: {ARTIFACTS_DIR}")
    print("\n=== Phase 4 anomaly detector training complete ===")
    return metadata


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    train_anomaly_detector()
