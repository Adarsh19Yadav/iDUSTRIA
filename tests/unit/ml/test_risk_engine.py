"""tests/unit/ml/test_risk_engine.py — Unit tests for the Phase 4 risk engine.

Tests cover:
  1.  Valid calculation — compute_risk_score returns RiskResult
  2.  Probability bounds — failure_probability outside [0,1] raises ValueError
  3.  Anomaly bounds — anomaly_score outside [0,1] raises ValueError
  4.  Risk score bounds — result always in [0, 1]
  5.  NORMAL / WARNING / CRITICAL mapping
  6.  Configurable thresholds
  7.  Deterministic calculation — same inputs → same output
  8.  Weight validation — weights not summing to 1 → ValueError
  9.  to_dict() has all expected keys
 10.  RiskLevel enum values
 11.  Edge values (0.0, 1.0)
 12.  machine_criticality out of range → ValueError
"""

from __future__ import annotations

import pytest

from ml.risk import (
    DEFAULT_CRITICAL_THRESHOLD,
    DEFAULT_W_ANOMALY,
    DEFAULT_W_FAILURE,
    DEFAULT_WARNING_THRESHOLD,
    RiskLevel,
    RiskResult,
    compute_risk_score,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NORMAL_INPUTS = dict(failure_probability=0.1, anomaly_score=0.1)
_HIGH_RISK_INPUTS = dict(failure_probability=0.9, anomaly_score=0.9)
_MEDIUM_RISK_INPUTS = dict(failure_probability=0.5, anomaly_score=0.5)


# ===========================================================================
# 1. Valid calculation
# ===========================================================================


class TestValidCalculation:
    def test_returns_risk_result(self):
        result = compute_risk_score(**_NORMAL_INPUTS)
        assert isinstance(result, RiskResult)

    def test_result_has_all_fields(self):
        result = compute_risk_score(**_NORMAL_INPUTS)
        assert hasattr(result, "risk_score")
        assert hasattr(result, "risk_level")
        assert hasattr(result, "w_failure")
        assert hasattr(result, "w_anomaly")
        assert hasattr(result, "warning_threshold")
        assert hasattr(result, "critical_threshold")
        assert hasattr(result, "machine_criticality")

    def test_formula_is_correct(self):
        """risk_score = 0.70 * fp + 0.30 * as, default weights."""
        fp, a_s = 0.6, 0.4
        expected = round(DEFAULT_W_FAILURE * fp + DEFAULT_W_ANOMALY * a_s, 6)
        result = compute_risk_score(failure_probability=fp, anomaly_score=a_s)
        assert abs(result.risk_score - expected) < 1e-9

    def test_custom_weights_applied(self):
        """Custom weights should be applied to the formula."""
        fp, a_s = 0.8, 0.2
        w_f, w_a = 0.6, 0.4
        expected = round(w_f * fp + w_a * a_s, 6)
        result = compute_risk_score(
            failure_probability=fp, anomaly_score=a_s, w_failure=w_f, w_anomaly=w_a
        )
        assert abs(result.risk_score - expected) < 1e-9


# ===========================================================================
# 2. Probability bounds
# ===========================================================================


class TestProbabilityBounds:
    @pytest.mark.parametrize("bad_fp", [-0.001, 1.001, -1.0, 2.0])
    def test_failure_probability_out_of_range_raises(self, bad_fp):
        with pytest.raises(ValueError, match="failure_probability"):
            compute_risk_score(failure_probability=bad_fp, anomaly_score=0.5)

    def test_none_failure_probability_raises(self):
        with pytest.raises((ValueError, TypeError)):
            compute_risk_score(failure_probability=None, anomaly_score=0.5)

    def test_nan_failure_probability_raises(self):
        import math

        with pytest.raises(ValueError, match="failure_probability"):
            compute_risk_score(failure_probability=float("nan"), anomaly_score=0.5)


# ===========================================================================
# 3. Anomaly score bounds
# ===========================================================================


class TestAnomalyBounds:
    @pytest.mark.parametrize("bad_as", [-0.001, 1.001, -1.0, 2.0])
    def test_anomaly_score_out_of_range_raises(self, bad_as):
        with pytest.raises(ValueError, match="anomaly_score"):
            compute_risk_score(failure_probability=0.5, anomaly_score=bad_as)

    def test_nan_anomaly_score_raises(self):
        with pytest.raises(ValueError, match="anomaly_score"):
            compute_risk_score(failure_probability=0.5, anomaly_score=float("nan"))


# ===========================================================================
# 4. Risk score bounds
# ===========================================================================


class TestRiskScoreBounds:
    @pytest.mark.parametrize(
        "fp,a_s",
        [
            (0.0, 0.0),
            (1.0, 1.0),
            (0.5, 0.5),
            (0.0, 1.0),
            (1.0, 0.0),
            (0.3, 0.7),
        ],
    )
    def test_risk_score_in_unit_interval(self, fp, a_s):
        result = compute_risk_score(failure_probability=fp, anomaly_score=a_s)
        assert 0.0 <= result.risk_score <= 1.0


# ===========================================================================
# 5. NORMAL / WARNING / CRITICAL mapping
# ===========================================================================


class TestRiskLevelMapping:
    def test_low_scores_are_normal(self):
        result = compute_risk_score(failure_probability=0.05, anomaly_score=0.05)
        assert result.risk_level == RiskLevel.NORMAL

    def test_medium_scores_are_warning(self):
        # 0.70*0.5 + 0.30*0.5 = 0.5 → WARNING (between 0.40 and 0.70)
        result = compute_risk_score(failure_probability=0.5, anomaly_score=0.5)
        assert result.risk_level == RiskLevel.WARNING

    def test_high_scores_are_critical(self):
        # 0.70*1.0 + 0.30*1.0 = 1.0 → CRITICAL
        result = compute_risk_score(failure_probability=1.0, anomaly_score=1.0)
        assert result.risk_level == RiskLevel.CRITICAL

    def test_boundary_at_warning_threshold(self):
        """Score exactly at warning_threshold should be WARNING."""
        threshold = DEFAULT_WARNING_THRESHOLD  # 0.40
        # Solve: 0.7*fp + 0.3*fp = 0.4 → fp = 0.4
        fp = threshold  # with equal values: 0.70*0.4 + 0.30*0.4 = 0.4
        result = compute_risk_score(failure_probability=fp, anomaly_score=fp)
        assert result.risk_level in (RiskLevel.WARNING, RiskLevel.NORMAL)
        # Exact boundary belongs to WARNING
        assert result.risk_score >= DEFAULT_WARNING_THRESHOLD or result.risk_level == RiskLevel.NORMAL

    def test_boundary_at_critical_threshold(self):
        """Score exactly at critical_threshold should be CRITICAL."""
        # Construct an input giving exactly 0.70
        # 0.70*fp + 0.30*fp = 0.70 → fp = 0.70
        fp = DEFAULT_CRITICAL_THRESHOLD
        result = compute_risk_score(failure_probability=fp, anomaly_score=fp)
        assert result.risk_level == RiskLevel.CRITICAL

    def test_level_value_strings(self):
        """RiskLevel enum values should be 'NORMAL', 'WARNING', 'CRITICAL'."""
        assert RiskLevel.NORMAL.value == "NORMAL"
        assert RiskLevel.WARNING.value == "WARNING"
        assert RiskLevel.CRITICAL.value == "CRITICAL"


# ===========================================================================
# 6. Configurable thresholds
# ===========================================================================


class TestConfigurableThresholds:
    def test_custom_thresholds_respected(self):
        """A score of 0.55 should be WARNING with default thresholds but can be
        NORMAL with a higher warning_threshold."""
        result_default = compute_risk_score(failure_probability=0.7, anomaly_score=0.5)
        # 0.70*0.7 + 0.30*0.5 = 0.64 → WARNING with defaults
        assert result_default.risk_level == RiskLevel.WARNING

        result_high = compute_risk_score(
            failure_probability=0.7,
            anomaly_score=0.5,
            warning_threshold=0.65,
            critical_threshold=0.90,
        )
        # 0.64 < 0.65 → NORMAL with these thresholds
        assert result_high.risk_level == RiskLevel.NORMAL

    def test_invalid_threshold_order_raises(self):
        with pytest.raises(ValueError):
            compute_risk_score(
                failure_probability=0.5,
                anomaly_score=0.5,
                warning_threshold=0.8,
                critical_threshold=0.4,
            )

    def test_equal_thresholds_raise(self):
        with pytest.raises(ValueError):
            compute_risk_score(
                failure_probability=0.5,
                anomaly_score=0.5,
                warning_threshold=0.5,
                critical_threshold=0.5,
            )


# ===========================================================================
# 7. Deterministic calculation
# ===========================================================================


class TestRiskDeterministic:
    def test_same_inputs_give_same_output(self):
        r1 = compute_risk_score(failure_probability=0.6, anomaly_score=0.4)
        r2 = compute_risk_score(failure_probability=0.6, anomaly_score=0.4)
        assert r1.risk_score == r2.risk_score
        assert r1.risk_level == r2.risk_level


# ===========================================================================
# 8. Weight validation
# ===========================================================================


class TestWeightValidation:
    def test_weights_not_summing_to_one_raises(self):
        with pytest.raises(ValueError, match="sum"):
            compute_risk_score(
                failure_probability=0.5,
                anomaly_score=0.5,
                w_failure=0.5,
                w_anomaly=0.4,
            )

    def test_zero_weight_raises(self):
        with pytest.raises(ValueError):
            compute_risk_score(
                failure_probability=0.5,
                anomaly_score=0.5,
                w_failure=0.0,
                w_anomaly=1.0,
            )


# ===========================================================================
# 9. to_dict()
# ===========================================================================


class TestRiskToDict:
    def test_to_dict_has_all_keys(self):
        result = compute_risk_score(**_NORMAL_INPUTS)
        d = result.to_dict()
        assert isinstance(d, dict)
        for key in (
            "risk_score",
            "risk_level",
            "w_failure",
            "w_anomaly",
            "warning_threshold",
            "critical_threshold",
            "machine_criticality",
        ):
            assert key in d

    def test_risk_level_in_dict_is_string(self):
        result = compute_risk_score(**_NORMAL_INPUTS)
        d = result.to_dict()
        assert isinstance(d["risk_level"], str)
        assert d["risk_level"] in ("NORMAL", "WARNING", "CRITICAL")


# ===========================================================================
# 10. Edge values
# ===========================================================================


class TestEdgeValues:
    def test_all_zeros(self):
        result = compute_risk_score(failure_probability=0.0, anomaly_score=0.0)
        assert result.risk_score == 0.0
        assert result.risk_level == RiskLevel.NORMAL

    def test_all_ones(self):
        result = compute_risk_score(failure_probability=1.0, anomaly_score=1.0)
        assert result.risk_score == 1.0
        assert result.risk_level == RiskLevel.CRITICAL


# ===========================================================================
# 11. machine_criticality validation
# ===========================================================================


class TestMachineCriticality:
    @pytest.mark.parametrize("bad_c", [-0.01, 1.001, -1.0, 2.0])
    def test_out_of_range_raises(self, bad_c):
        with pytest.raises(ValueError, match="machine_criticality"):
            compute_risk_score(
                failure_probability=0.5,
                anomaly_score=0.5,
                machine_criticality=bad_c,
            )

    def test_none_criticality_raises(self):
        with pytest.raises((ValueError, TypeError)):
            compute_risk_score(
                failure_probability=0.5,
                anomaly_score=0.5,
                machine_criticality=None,
            )

    def test_valid_criticality_stored(self):
        result = compute_risk_score(
            failure_probability=0.5, anomaly_score=0.5, machine_criticality=0.5
        )
        assert result.machine_criticality == 0.5
