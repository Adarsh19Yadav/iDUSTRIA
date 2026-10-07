"""ml/assessment.py — Phase 4 Combined Machine Assessment.

This module provides the top-level ``assess_machine`` function that orchestrates
Phase 3 failure prediction and Phase 4 anomaly detection into a single,
deterministic machine assessment result.

This function is the primary interface for the INDUSTRIA-X API and agent.

OUTPUT
------
AssessmentResult contains:
  - failure_probability  : float [0, 1]  — Phase 3 XGBoost prediction
  - predicted_failure    : int  {0, 1}   — Threshold-applied failure class
  - anomaly_score        : float [0, 1]  — Normalised anomaly severity (not a probability)
  - is_anomaly           : bool          — True if observation is an outlier
  - risk_score           : float [0, 1]  — Weighted composite risk
  - risk_level           : str           — NORMAL / WARNING / CRITICAL

DETERMINISM
-----------
For the same inputs and model artifacts, this function always returns the
same result.  It performs no sampling or randomness at inference time.

DISCLAIMERS
-----------
- Anomaly detection identifies unusual operating patterns; it does NOT prove
  that a machine is failing.
- The unified risk score is a prototype decision-support score and is NOT
  an industrial safety certification.
- All models were trained on the AI4I 2020 *synthetic* dataset.

Usage
-----
    from ml.assessment import assess_machine

    result = assess_machine(
        air_temp_k=300.5,
        process_temp_k=310.2,
        rotational_speed_rpm=1500,
        torque_nm=40.0,
        tool_wear_min=120,
        type_="M",
    )
    print(result.to_dict())
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from ml.anomaly_inference import AnomalyResult, detect_anomaly
from ml.inference import InferenceResult, predict_failure
from ml.risk import (
    DEFAULT_CRITICAL_THRESHOLD,
    DEFAULT_W_ANOMALY,
    DEFAULT_W_FAILURE,
    DEFAULT_WARNING_THRESHOLD,
    RiskLevel,
    compute_risk_score,
)

# ---------------------------------------------------------------------------
# Valid categories
# ---------------------------------------------------------------------------

_VALID_TYPES: frozenset[str] = frozenset({"L", "M", "H"})

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssessmentResult:
    """Return type of :func:`assess_machine`.

    Attributes
    ----------
    failure_probability:
        Calibrated failure probability from Phase 3 XGBoost model.
        Float in [0, 1].
    predicted_failure:
        0 or 1, determined by the Phase 3 classification threshold (0.543).
    anomaly_score:
        Normalised anomaly severity in [0, 1].  This is NOT a probability.
        1 = maximally anomalous relative to training data.
    is_anomaly:
        True when the observation is classified as an outlier by the
        Phase 4 IsolationForest (raw decision_function score < 0).
    risk_score:
        Weighted composite score in [0, 1].
        Formula: 0.70 × failure_probability + 0.30 × anomaly_score.
    risk_level:
        Decision-support category: 'NORMAL', 'WARNING', or 'CRITICAL'.
        NOT an industrial safety classification.
    failure_threshold:
        Failure classification threshold used (from Phase 3 metadata).
    model_version:
        Version tag for the failure model artifact.
    anomaly_version:
        Version tag for the anomaly detector artifact.
    machine_criticality:
        Criticality value provided (default 1.0).
    """

    failure_probability: float
    predicted_failure: int
    anomaly_score: float
    is_anomaly: bool
    risk_score: float
    risk_level: str
    failure_threshold: float
    model_version: str
    anomaly_version: str
    machine_criticality: float

    def to_dict(self) -> dict:
        return {
            "failure_probability": self.failure_probability,
            "predicted_failure": self.predicted_failure,
            "anomaly_score": self.anomaly_score,
            "is_anomaly": self.is_anomaly,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "failure_threshold": self.failure_threshold,
            "model_version": self.model_version,
            "anomaly_version": self.anomaly_version,
            "machine_criticality": self.machine_criticality,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def assess_machine(
    air_temp_k: float,
    process_temp_k: float,
    rotational_speed_rpm: float,
    torque_nm: float,
    tool_wear_min: float,
    type_: str,
    *,
    machine_criticality: float = 1.0,
    w_failure: float = DEFAULT_W_FAILURE,
    w_anomaly: float = DEFAULT_W_ANOMALY,
    warning_threshold: float = DEFAULT_WARNING_THRESHOLD,
    critical_threshold: float = DEFAULT_CRITICAL_THRESHOLD,
    artifacts_dir: str | Path | None = None,
) -> AssessmentResult:
    """Run a combined failure + anomaly assessment for one machine observation.

    Orchestrates:
      1. Phase 3 failure prediction  (:func:`ml.inference.predict_failure`)
      2. Phase 4 anomaly detection   (:func:`ml.anomaly_inference.detect_anomaly`)
      3. Phase 4 risk scoring        (:func:`ml.risk.compute_risk_score`)

    Parameters
    ----------
    air_temp_k:
        Air temperature in Kelvin.  Expected range: ~295–305 K.
    process_temp_k:
        Process temperature in Kelvin.  Expected range: ~305–315 K.
    rotational_speed_rpm:
        Rotational speed in RPM.  Expected range: ~1100–2900 rpm.
    torque_nm:
        Torque in Newton-metres.  Expected range: ~3–77 Nm.
    tool_wear_min:
        Cumulative tool wear in minutes.  Expected range: 0–254 min.
    type_:
        Product quality variant.  Must be one of ``'L'``, ``'M'``, ``'H'``.
    machine_criticality:
        Optional criticality rating in [0, 1].  Default 1.0.
        Not currently applied to the formula; stored for traceability.
    w_failure:
        Weight for failure_probability in risk formula.  Default 0.70.
    w_anomaly:
        Weight for anomaly_score in risk formula.  Default 0.30.
    warning_threshold:
        risk_score threshold for WARNING level.  Default 0.40.
    critical_threshold:
        risk_score threshold for CRITICAL level.  Default 0.70.
    artifacts_dir:
        Optional override for the artifacts directory.
        Defaults to ``ml/artifacts/v1``.

    Returns
    -------
    AssessmentResult
        Fully populated assessment dataclass.

    Raises
    ------
    ValueError
        If ``type_`` is invalid, any numeric feature is None/NaN,
        or ``machine_criticality`` is outside [0, 1].
    FileNotFoundError
        If any model artifact is missing.
    """
    # ------------------------------------------------------------------
    # Input validation (before loading any artifact)
    # ------------------------------------------------------------------
    if type_ not in _VALID_TYPES:
        raise ValueError(
            f"Invalid 'type_' value '{type_}'. Must be one of {sorted(_VALID_TYPES)}."
        )

    numeric_inputs = {
        "air_temp_k": air_temp_k,
        "process_temp_k": process_temp_k,
        "rotational_speed_rpm": rotational_speed_rpm,
        "torque_nm": torque_nm,
        "tool_wear_min": tool_wear_min,
    }
    for name, val in numeric_inputs.items():
        if val is None or (isinstance(val, float) and np.isnan(float(val))):
            raise ValueError(f"Feature '{name}' must not be None or NaN.")

    if machine_criticality is None or np.isnan(float(machine_criticality)):
        raise ValueError("'machine_criticality' must not be None or NaN.")
    if not (0.0 <= float(machine_criticality) <= 1.0):
        raise ValueError(
            f"'machine_criticality' must be in [0, 1], got {machine_criticality}."
        )

    # ------------------------------------------------------------------
    # 1. Failure prediction
    # ------------------------------------------------------------------
    failure_result: InferenceResult = predict_failure(
        air_temp_k=air_temp_k,
        process_temp_k=process_temp_k,
        rotational_speed_rpm=rotational_speed_rpm,
        torque_nm=torque_nm,
        tool_wear_min=tool_wear_min,
        type_=type_,
        artifacts_dir=artifacts_dir,
    )

    # ------------------------------------------------------------------
    # 2. Anomaly detection
    # ------------------------------------------------------------------
    anomaly_result: AnomalyResult = detect_anomaly(
        air_temp_k=air_temp_k,
        process_temp_k=process_temp_k,
        rotational_speed_rpm=rotational_speed_rpm,
        torque_nm=torque_nm,
        tool_wear_min=tool_wear_min,
        type_=type_,
        artifacts_dir=artifacts_dir,
    )

    # ------------------------------------------------------------------
    # 3. Risk scoring
    # ------------------------------------------------------------------
    risk_result = compute_risk_score(
        failure_probability=failure_result.failure_probability,
        anomaly_score=anomaly_result.anomaly_score,
        machine_criticality=machine_criticality,
        w_failure=w_failure,
        w_anomaly=w_anomaly,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
    )

    return AssessmentResult(
        failure_probability=failure_result.failure_probability,
        predicted_failure=failure_result.predicted_failure,
        anomaly_score=anomaly_result.anomaly_score,
        is_anomaly=anomaly_result.is_anomaly,
        risk_score=risk_result.risk_score,
        risk_level=risk_result.risk_level.value,
        failure_threshold=failure_result.threshold,
        model_version=failure_result.model_version,
        anomaly_version=anomaly_result.anomaly_version,
        machine_criticality=machine_criticality,
    )
