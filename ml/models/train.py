"""ml/models/train.py — Phase 3 model training and evaluation.

SYNTHETIC DATA NOTICE
---------------------
All results are derived from the AI4I 2020 synthetic dataset.
They do NOT represent real factory equipment performance.

MODELS TRAINED
--------------
  Model A: Logistic Regression (class_weight='balanced')
  Model B: Random Forest       (class_weight='balanced')
  Model C: XGBoost             (scale_pos_weight to handle imbalance)

IMBALANCE STRATEGY
------------------
Class-weight balancing is applied directly in models A and B.
XGBoost uses scale_pos_weight (ratio of negatives to positives in training set).
SMOTE is NOT used here — class weighting is sufficient and avoids
the risk of test-contamination if a pipeline is misconfigured.

THRESHOLD TUNING
----------------
For each model the classification threshold is optimised on the
training set (5-fold cross-validation predicted probabilities via
cross_val_predict) to maximise F1 for the failure class without
using any test-set information.

Usage
-----
    python -m ml.models.train
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import cross_val_predict
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from ml.data.features import build_preprocessor, get_X_y
from ml.data.loader import load_raw
from ml.data.splitting import SPLIT_CONFIG, make_split

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_VERSION = "v1"
ARTIFACTS_DIR = Path("ml/artifacts") / MODEL_VERSION
RANDOM_STATE = SPLIT_CONFIG["random_state"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_full_pipeline(classifier) -> Pipeline:
    """Wrap a classifier with the Phase 2 preprocessor into a full Pipeline."""
    return Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            ("classifier", classifier),
        ]
    )


def _tune_threshold_on_train(
    pipeline: Pipeline,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv: int = 5,
) -> float:
    """Select classification threshold that maximises failure-class F1.

    Uses cross_val_predict on the training set to obtain out-of-fold predicted
    probabilities.  The test set is never touched.

    Parameters
    ----------
    pipeline:
        Fitted or unfitted sklearn Pipeline ending with a classifier.
    X_train, y_train:
        Training features and labels.
    cv:
        Number of cross-validation folds.

    Returns
    -------
    float
        Threshold in [0, 1] that maximises F1 for class 1 on the OOF probabilities.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        oof_probs = cross_val_predict(
            pipeline,
            X_train,
            y_train,
            cv=cv,
            method="predict_proba",
        )[:, 1]

    precision, recall, thresholds = precision_recall_curve(y_train, oof_probs)
    # f1 = 2*p*r/(p+r); thresholds has one fewer element than p/r
    with np.errstate(divide="ignore", invalid="ignore"):
        f1_scores = np.where(
            (precision[:-1] + recall[:-1]) > 0,
            2 * precision[:-1] * recall[:-1] / (precision[:-1] + recall[:-1]),
            0.0,
        )
    best_idx = int(np.argmax(f1_scores))
    best_threshold = float(thresholds[best_idx])
    return best_threshold


def _evaluate(
    pipeline: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    threshold: float,
    label: str,
) -> dict:
    """Compute full evaluation metrics at a given threshold."""
    proba = pipeline.predict_proba(X)[:, 1]
    y_pred = (proba >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y, y_pred).ravel()
    roc_auc = roc_auc_score(y, proba)
    pr_auc = average_precision_score(y, proba)
    report = classification_report(y, y_pred, output_dict=True, zero_division=0)

    accuracy = (tp + tn) / (tp + tn + fp + fn)

    return {
        "model": label,
        "threshold": threshold,
        "accuracy": float(accuracy),
        "precision_failure": report["1"]["precision"],
        "recall_failure": report["1"]["recall"],
        "f1_failure": report["1"]["f1-score"],
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
    }


def _print_metrics(m: dict) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {m['model']}  (threshold = {m['threshold']:.3f})")
    print(f"{'=' * 60}")
    print(f"  Accuracy          : {m['accuracy']:.4f}")
    print(f"  Failure Precision : {m['precision_failure']:.4f}")
    print(f"  Failure Recall    : {m['recall_failure']:.4f}")
    print(f"  Failure F1        : {m['f1_failure']:.4f}")
    print(f"  ROC-AUC           : {m['roc_auc']:.4f}")
    print(f"  PR-AUC            : {m['pr_auc']:.4f}")
    print(f"  TP={m['tp']}  FP={m['fp']}  TN={m['tn']}  FN={m['fn']}")
    print(f"  Confusion matrix  : TN={m['tn']} FP={m['fp']} / FN={m['fn']} TP={m['tp']}")


# ---------------------------------------------------------------------------
# Main training routine
# ---------------------------------------------------------------------------


def train_and_evaluate() -> dict:
    """Run the full Phase 3 training and evaluation pipeline.

    Returns
    -------
    dict
        A results dict containing metrics for all models and the chosen
        final model name.
    """
    print("=== INDUSTRIA-X Phase 3 — Machine Failure Prediction ===\n")

    # ------------------------------------------------------------------
    # 1. Load data and split
    # ------------------------------------------------------------------
    print("[1/6] Loading dataset …")
    df = load_raw()
    X, y = get_X_y(df)
    X_train, X_test, y_train, y_test = make_split(X, y)

    n_neg = int((y_train == 0).sum())
    n_pos = int((y_train == 1).sum())
    scale_pos_weight = n_neg / n_pos  # for XGBoost

    print(f"      Train: {len(y_train)} rows  ({n_pos} failures, {n_pos / len(y_train):.2%})")
    print(f"      Test : {len(y_test)} rows  ({int(y_test.sum())} failures, {y_test.mean():.2%})")
    print(f"      scale_pos_weight (XGBoost): {scale_pos_weight:.2f}")

    # ------------------------------------------------------------------
    # 2. Define models
    # ------------------------------------------------------------------
    print("\n[2/6] Defining models …")

    model_configs: list[tuple[str, Pipeline]] = [
        (
            "Logistic Regression",
            _build_full_pipeline(
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=RANDOM_STATE,
                    solver="lbfgs",
                )
            ),
        ),
        (
            "Random Forest",
            _build_full_pipeline(
                RandomForestClassifier(
                    n_estimators=200,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                )
            ),
        ),
        (
            "XGBoost",
            _build_full_pipeline(
                XGBClassifier(
                    n_estimators=200,
                    scale_pos_weight=scale_pos_weight,
                    random_state=RANDOM_STATE,
                    eval_metric="logloss",
                    verbosity=0,
                    use_label_encoder=False,
                )
            ),
        ),
    ]

    # ------------------------------------------------------------------
    # 3. Tune thresholds on training data (OOF cross-validation)
    # ------------------------------------------------------------------
    print("\n[3/6] Tuning thresholds on training data (5-fold OOF) …")

    tuned_thresholds: dict[str, float] = {}
    for name, pipeline in model_configs:
        print(f"      Tuning '{name}' …", end=" ", flush=True)
        t = _tune_threshold_on_train(pipeline, X_train, y_train, cv=5)
        tuned_thresholds[name] = t
        print(f"threshold = {t:.3f}")

    # ------------------------------------------------------------------
    # 4. Fit final models on full training set
    # ------------------------------------------------------------------
    print("\n[4/6] Fitting models on full training set …")

    fitted_pipelines: dict[str, Pipeline] = {}
    for name, pipeline in model_configs:
        print(f"      Fitting '{name}' …", end=" ", flush=True)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pipeline.fit(X_train, y_train)
        fitted_pipelines[name] = pipeline
        print("done.")

    # ------------------------------------------------------------------
    # 5. Evaluate on test set
    # ------------------------------------------------------------------
    print("\n[5/6] Evaluating on held-out test set …")

    results: list[dict] = []
    for name, pipeline in fitted_pipelines.items():
        threshold = tuned_thresholds[name]
        m = _evaluate(pipeline, X_test, y_test, threshold, name)
        results.append(m)
        _print_metrics(m)

    # ------------------------------------------------------------------
    # 6. Model selection
    # ------------------------------------------------------------------
    print("\n[6/6] Selecting final model …")

    # Selection criterion: best PR-AUC as primary metric (summary of
    # precision-recall trade-off across all thresholds), then F1 as
    # tie-breaker — both measured on the held-out test set.
    best = max(results, key=lambda m: (m["pr_auc"], m["f1_failure"]))
    print(f"\n  [SELECTED] Final model: {best['model']}")
    print(f"     PR-AUC      : {best['pr_auc']:.4f}")
    print(f"     F1-failure  : {best['f1_failure']:.4f}")
    print(f"     Threshold   : {best['threshold']:.3f}")

    output = {
        "model_version": MODEL_VERSION,
        "split_config": SPLIT_CONFIG,
        "train_size": len(y_train),
        "test_size": len(y_test),
        "train_failures": n_pos,
        "test_failures": int(y_test.sum()),
        "models": results,
        "selected_model": best["model"],
        "selected_threshold": best["threshold"],
    }

    return output, fitted_pipelines, tuned_thresholds


# ---------------------------------------------------------------------------
# Artifact persistence
# ---------------------------------------------------------------------------


def save_artifacts(
    output: dict,
    fitted_pipelines: dict[str, Pipeline],
    tuned_thresholds: dict[str, float],
) -> None:
    """Persist all training artifacts to ARTIFACTS_DIR."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    selected_name = output["selected_model"]
    selected_pipeline = fitted_pipelines[selected_name]
    selected_threshold = tuned_thresholds[selected_name]

    # Save final model pipeline
    pipeline_path = ARTIFACTS_DIR / "model_pipeline.joblib"
    joblib.dump(selected_pipeline, pipeline_path)
    print(f"\n  Saved: {pipeline_path}")

    # Save model metadata
    from ml.data.features import FEATURE_COLUMNS, NUMERICAL_FEATURES, CATEGORICAL_FEATURES

    metadata = {
        "model_version": MODEL_VERSION,
        "model_name": selected_name,
        "threshold": selected_threshold,
        "feature_columns": FEATURE_COLUMNS,
        "numerical_features": NUMERICAL_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "target_column": "Machine failure",
        "dataset": "AI4I 2020 Predictive Maintenance Dataset (synthetic)",
        "split_config": SPLIT_CONFIG,
        "train_size": output["train_size"],
        "test_size": output["test_size"],
        "train_failures": output["train_failures"],
        "test_failures": output["test_failures"],
        "evaluation_metrics": {
            m["model"]: {k: v for k, v in m.items() if k != "model"}
            for m in output["models"]
        },
    }
    metadata_path = ARTIFACTS_DIR / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Saved: {metadata_path}")

    print(f"\n  All artifacts saved to: {ARTIFACTS_DIR}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    output, fitted_pipelines, tuned_thresholds = train_and_evaluate()
    save_artifacts(output, fitted_pipelines, tuned_thresholds)
    print("\n=== Phase 3 training complete ===")
