"""ml/risk.py — Phase 4 Unified Machine Risk Engine.

OVERVIEW
--------
Combines the Phase 3 failure probability with Phase 4 anomaly severity to
produce a single ``risk_score`` in [0, 1] and a categorical ``risk_level``.

FORMULA
-------
    risk_score = w_failure × failure_probability
               + w_anomaly × anomaly_score

Default weights (configurable):
    w_failure = 0.70  (failure probability dominates — it is a calibrated ML signal)
    w_anomaly = 0.30  (anomaly score adds sensitivity to unusual patterns)

Weights must sum to 1.0.

MACHINE CRITICALITY
-------------------
The AI4I 2020 dataset does not include machine-criticality ratings.
A ``machine_criticality`` parameter (float in [0, 1]) is accepted but
currently not used to modify the formula — it is stored in the assessment
result for traceability and future use.

When criticality becomes available, a natural extension is:

    risk_score = baseline_risk × (1 + criticality_boost × machine_criticality)

For now, the default ``machine_criticality = 1.0`` (maximum criticality as a
conservative safe-side default).  Operators may pass a lower value to reflect
a non-critical machine.

RISK LEVELS
-----------
Configurable thresholds map risk_score to three named levels:

    NORMAL   : risk_score < WARNING_THRESHOLD
    WARNING  : WARNING_THRESHOLD ≤ risk_score < CRITICAL_THRESHOLD
    CRITICAL : risk_score ≥ CRITICAL_THRESHOLD

Defaults:
    WARNING_THRESHOLD  = 0.40
    CRITICAL_THRESHOLD = 0.70

These are decision-support categories for a prototype system.
They are NOT certified industrial safety classifications.

IMPORTANT DISCLAIMER
--------------------
The unified risk score is a prototype decision-support score.
It is NOT an industrial safety certification.

Usage
-----
    from ml.risk import compute_risk_score, RiskLevel

    score, level = compute_risk_score(
        failure_probability=0.75,
        anomaly_score=0.60,
    )
    # score ≈ 0.705, level = RiskLevel.CRITICAL
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------
# Default weights and thresholds (configurable via parameters)
# ---------------------------------------------------------------------------

#: Default weight for the failure probability component.
DEFAULT_W_FAILURE: float = 0.70

#: Default weight for the anomaly score component.
DEFAULT_W_ANOMALY: float = 0.30

#: risk_score below this is NORMAL.
DEFAULT_WARNING_THRESHOLD: float = 0.40

#: risk_score at or above this is CRITICAL.
DEFAULT_CRITICAL_THRESHOLD: float = 0.70

# ---------------------------------------------------------------------------
# Risk level enumeration
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    """Categorical risk classification.

    These are decision-support categories, NOT industrial safety certifications.
    """

    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RiskResult:
    """Output of :func:`compute_risk_score`.

    Attributes
    ----------
    risk_score:
        Weighted composite score in [0, 1].  Higher = more risk.
    risk_level:
        Categorical level: NORMAL / WARNING / CRITICAL.
    w_failure:
        Weight applied to failure_probability.
    w_anomaly:
        Weight applied to anomaly_score.
    warning_threshold:
        Threshold at or above which level becomes WARNING.
    critical_threshold:
        Threshold at or above which level becomes CRITICAL.
    machine_criticality:
        Stored for traceability; not currently applied to formula.
    """

    risk_score: float
    risk_level: RiskLevel
    w_failure: float
    w_anomaly: float
    warning_threshold: float
    critical_threshold: float
    machine_criticality: float

    def to_dict(self) -> dict:
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "w_failure": self.w_failure,
            "w_anomaly": self.w_anomaly,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "machine_criticality": self.machine_criticality,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_risk_score(
    failure_probability: float,
    anomaly_score: float,
    *,
    machine_criticality: float = 1.0,
    w_failure: float = DEFAULT_W_FAILURE,
    w_anomaly: float = DEFAULT_W_ANOMALY,
    warning_threshold: float = DEFAULT_WARNING_THRESHOLD,
    critical_threshold: float = DEFAULT_CRITICAL_THRESHOLD,
) -> RiskResult:
    """Compute a unified machine risk score.

    The formula is:

        risk_score = w_failure × failure_probability + w_anomaly × anomaly_score

    Parameters
    ----------
    failure_probability:
        Failure probability from Phase 3 model.  Must be in [0, 1].
    anomaly_score:
        Normalised anomaly score from Phase 4 detector.  Must be in [0, 1].
        This is NOT a probability — it is a normalised severity index.
    machine_criticality:
        Optional criticality rating in [0, 1].  Default 1.0 (maximum).
        Stored in output for traceability; not currently applied to formula.
    w_failure:
        Weight for failure_probability.  Default 0.70.
    w_anomaly:
        Weight for anomaly_score.  Default 0.30.
    warning_threshold:
        risk_score at which level transitions from NORMAL to WARNING.
        Default 0.40.
    critical_threshold:
        risk_score at which level transitions from WARNING to CRITICAL.
        Default 0.70.

    Returns
    -------
    RiskResult
        Dataclass with risk_score, risk_level, and configuration parameters.

    Raises
    ------
    ValueError
        If any input is outside its valid range or if weights do not sum to 1.
    """
    # ------------------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------------------
    _validate_probability(failure_probability, "failure_probability")
    _validate_unit_interval(anomaly_score, "anomaly_score")
    _validate_unit_interval(machine_criticality, "machine_criticality")

    if not (0.0 < w_failure <= 1.0):
        raise ValueError(f"w_failure must be in (0, 1], got {w_failure}.")
    if not (0.0 < w_anomaly <= 1.0):
        raise ValueError(f"w_anomaly must be in (0, 1], got {w_anomaly}.")
    if abs(w_failure + w_anomaly - 1.0) > 1e-9:
        raise ValueError(
            f"Weights must sum to 1.0, got w_failure={w_failure} + w_anomaly={w_anomaly} "
            f"= {w_failure + w_anomaly:.6f}."
        )
    if not (0.0 <= warning_threshold < critical_threshold <= 1.0):
        raise ValueError(
            f"Thresholds must satisfy 0 ≤ warning_threshold < critical_threshold ≤ 1. "
            f"Got warning={warning_threshold}, critical={critical_threshold}."
        )

    # ------------------------------------------------------------------
    # Compute risk score  (deterministic Python arithmetic — not LLM)
    # ------------------------------------------------------------------
    raw = w_failure * failure_probability + w_anomaly * anomaly_score
    # Clip to [0, 1] to guard against floating-point overshoot
    risk_score = float(np.clip(raw, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Classify
    # ------------------------------------------------------------------
    if risk_score >= critical_threshold:
        level = RiskLevel.CRITICAL
    elif risk_score >= warning_threshold:
        level = RiskLevel.WARNING
    else:
        level = RiskLevel.NORMAL

    return RiskResult(
        risk_score=round(risk_score, 6),
        risk_level=level,
        w_failure=w_failure,
        w_anomaly=w_anomaly,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
        machine_criticality=machine_criticality,
    )


# ---------------------------------------------------------------------------
# Internal validators
# ---------------------------------------------------------------------------


def _validate_probability(value: object, name: str) -> None:
    """Raise ValueError if value is not a float in [0, 1] and not NaN/None."""
    _validate_unit_interval(value, name)


def _validate_unit_interval(value: object, name: str) -> None:
    """Raise ValueError if value is not a number in [0, 1] or is NaN/None."""
    if value is None:
        raise ValueError(f"'{name}' must not be None.")
    if not isinstance(value, (int, float)):
        raise ValueError(f"'{name}' must be a number, got {type(value).__name__}.")
    if np.isnan(float(value)):
        raise ValueError(f"'{name}' must not be NaN.")
    if not (0.0 <= float(value) <= 1.0):
        raise ValueError(f"'{name}' must be in [0, 1], got {value}.")
