"""tests/unit/ml/test_assessment.py — Unit tests for Phase 4 combined machine assessment.

Tests cover:
  1.  Valid machine assessment — assess_machine returns AssessmentResult
  2.  All required fields present
  3.  Output field ranges
  4.  Missing input (None / NaN numeric) → ValueError
  5.  Invalid type_ → ValueError
  6.  Invalid machine_criticality → ValueError
  7.  Missing failure model artifact → FileNotFoundError
  8.  Missing anomaly artifact → FileNotFoundError
  9.  Deterministic output
 10.  to_dict() returns all expected keys
 11.  Risk level is a valid string
 12.  Predicted failure is 0 or 1
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NORMAL_OBS = dict(
    air_temp_k=300.0,
    process_temp_k=310.0,
    rotational_speed_rpm=1500,
    torque_nm=40.0,
    tool_wear_min=100,
    type_="M",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_all_caches():
    """Clear both model caches before and after each test."""
    from ml.anomaly_inference import _AnomalyCache
    from ml.inference import _ModelCache

    _ModelCache.clear_cache()
    _AnomalyCache.clear_cache()
    yield
    _ModelCache.clear_cache()
    _AnomalyCache.clear_cache()


@pytest.fixture
def real_artifacts_dir() -> Path:
    return Path("ml/artifacts/v1")


@pytest.fixture
def fake_artifacts(tmp_path, real_artifacts_dir):
    """Copy both failure and anomaly artifacts into a tmp directory."""
    dst = tmp_path / "v1"
    dst.mkdir()
    for fname in (
        "model_pipeline.joblib",
        "metadata.json",
        "anomaly_pipeline.joblib",
        "anomaly_metadata.json",
    ):
        shutil.copy(real_artifacts_dir / fname, dst / fname)
    return dst


@pytest.fixture
def missing_anomaly_artifacts(tmp_path, real_artifacts_dir):
    """Copy only the failure model artifacts (no anomaly files)."""
    dst = tmp_path / "v1"
    dst.mkdir()
    shutil.copy(real_artifacts_dir / "model_pipeline.joblib", dst / "model_pipeline.joblib")
    shutil.copy(real_artifacts_dir / "metadata.json", dst / "metadata.json")
    return dst


@pytest.fixture
def missing_failure_artifacts(tmp_path, real_artifacts_dir):
    """Copy only the anomaly artifacts (no failure model files)."""
    dst = tmp_path / "v1"
    dst.mkdir()
    shutil.copy(
        real_artifacts_dir / "anomaly_pipeline.joblib", dst / "anomaly_pipeline.joblib"
    )
    shutil.copy(
        real_artifacts_dir / "anomaly_metadata.json", dst / "anomaly_metadata.json"
    )
    return dst


# ===========================================================================
# 1. Valid machine assessment
# ===========================================================================


class TestValidAssessment:
    def test_returns_assessment_result(self, fake_artifacts):
        from ml.assessment import AssessmentResult, assess_machine

        result = assess_machine(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert isinstance(result, AssessmentResult)

    def test_all_required_fields_present(self, fake_artifacts):
        from ml.assessment import assess_machine

        result = assess_machine(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        for field in (
            "failure_probability",
            "predicted_failure",
            "anomaly_score",
            "is_anomaly",
            "risk_score",
            "risk_level",
            "failure_threshold",
            "model_version",
            "anomaly_version",
            "machine_criticality",
        ):
            assert hasattr(result, field), f"Missing field: {field}"


# ===========================================================================
# 2. Output field ranges
# ===========================================================================


class TestAssessmentFieldRanges:
    def test_failure_probability_in_unit_interval(self, fake_artifacts):
        from ml.assessment import assess_machine

        result = assess_machine(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert 0.0 <= result.failure_probability <= 1.0

    def test_anomaly_score_in_unit_interval(self, fake_artifacts):
        from ml.assessment import assess_machine

        result = assess_machine(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert 0.0 <= result.anomaly_score <= 1.0

    def test_risk_score_in_unit_interval(self, fake_artifacts):
        from ml.assessment import assess_machine

        result = assess_machine(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert 0.0 <= result.risk_score <= 1.0

    def test_predicted_failure_is_0_or_1(self, fake_artifacts):
        from ml.assessment import assess_machine

        result = assess_machine(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert result.predicted_failure in (0, 1)

    def test_is_anomaly_is_bool(self, fake_artifacts):
        from ml.assessment import assess_machine

        result = assess_machine(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert isinstance(result.is_anomaly, bool)

    def test_risk_level_is_valid_string(self, fake_artifacts):
        from ml.assessment import assess_machine

        result = assess_machine(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert result.risk_level in ("NORMAL", "WARNING", "CRITICAL")


# ===========================================================================
# 3. Missing/invalid numeric inputs
# ===========================================================================


class TestAssessmentMissingInput:
    @pytest.mark.parametrize(
        "field,value",
        [
            ("air_temp_k", None),
            ("process_temp_k", None),
            ("rotational_speed_rpm", None),
            ("torque_nm", None),
            ("tool_wear_min", None),
            ("air_temp_k", float("nan")),
            ("torque_nm", float("nan")),
        ],
    )
    def test_none_or_nan_numeric_raises(self, field, value, fake_artifacts):
        from ml.assessment import assess_machine

        obs = dict(_NORMAL_OBS)
        obs[field] = value
        with pytest.raises(ValueError, match=field):
            assess_machine(**obs, artifacts_dir=fake_artifacts)


# ===========================================================================
# 4. Invalid type_
# ===========================================================================


class TestAssessmentInvalidType:
    @pytest.mark.parametrize("bad_type", ["X", "Z", "l", "m", "h", "", "LMH"])
    def test_invalid_type_raises(self, bad_type, fake_artifacts):
        from ml.assessment import assess_machine

        obs = dict(_NORMAL_OBS)
        obs["type_"] = bad_type
        with pytest.raises(ValueError, match="type_"):
            assess_machine(**obs, artifacts_dir=fake_artifacts)


# ===========================================================================
# 5. Invalid machine_criticality
# ===========================================================================


class TestAssessmentInvalidCriticality:
    @pytest.mark.parametrize("bad_c", [-0.01, 1.001, -1.0, 2.0])
    def test_out_of_range_criticality_raises(self, bad_c, fake_artifacts):
        from ml.assessment import assess_machine

        with pytest.raises(ValueError, match="machine_criticality"):
            assess_machine(**_NORMAL_OBS, machine_criticality=bad_c, artifacts_dir=fake_artifacts)

    def test_none_criticality_raises(self, fake_artifacts):
        from ml.assessment import assess_machine

        with pytest.raises((ValueError, TypeError)):
            assess_machine(**_NORMAL_OBS, machine_criticality=None, artifacts_dir=fake_artifacts)


# ===========================================================================
# 6. Missing failure model artifact
# ===========================================================================


class TestAssessmentMissingFailureArtifact:
    def test_missing_failure_model_raises_file_not_found(self, missing_failure_artifacts):
        from ml.assessment import assess_machine

        with pytest.raises(FileNotFoundError, match="model_pipeline"):
            assess_machine(**_NORMAL_OBS, artifacts_dir=missing_failure_artifacts)


# ===========================================================================
# 7. Missing anomaly artifact
# ===========================================================================


class TestAssessmentMissingAnomalyArtifact:
    def test_missing_anomaly_model_raises_file_not_found(self, missing_anomaly_artifacts):
        from ml.assessment import assess_machine

        with pytest.raises(FileNotFoundError, match="anomaly_pipeline"):
            assess_machine(**_NORMAL_OBS, artifacts_dir=missing_anomaly_artifacts)


# ===========================================================================
# 8. Deterministic output
# ===========================================================================


class TestAssessmentDeterministic:
    def test_same_input_gives_same_output(self, fake_artifacts):
        from ml.assessment import assess_machine

        r1 = assess_machine(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        r2 = assess_machine(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert r1.failure_probability == r2.failure_probability
        assert r1.anomaly_score == r2.anomaly_score
        assert r1.risk_score == r2.risk_score
        assert r1.risk_level == r2.risk_level

    def test_different_inputs_run_without_error(self, fake_artifacts):
        """Both normal and stressed observations should run cleanly."""
        from ml.assessment import assess_machine

        normal = assess_machine(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        stressed = assess_machine(
            air_temp_k=303.0,
            process_temp_k=313.0,
            rotational_speed_rpm=1200,
            torque_nm=68.0,
            tool_wear_min=240,
            type_="L",
            artifacts_dir=fake_artifacts,
        )
        assert 0.0 <= normal.risk_score <= 1.0
        assert 0.0 <= stressed.risk_score <= 1.0


# ===========================================================================
# 9. to_dict()
# ===========================================================================


class TestAssessmentToDict:
    def test_to_dict_returns_all_keys(self, fake_artifacts):
        from ml.assessment import assess_machine

        result = assess_machine(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        d = result.to_dict()
        assert isinstance(d, dict)
        for key in (
            "failure_probability",
            "predicted_failure",
            "anomaly_score",
            "is_anomaly",
            "risk_score",
            "risk_level",
            "failure_threshold",
            "model_version",
            "anomaly_version",
            "machine_criticality",
        ):
            assert key in d

    def test_to_dict_values_match_result(self, fake_artifacts):
        from ml.assessment import assess_machine

        result = assess_machine(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        d = result.to_dict()
        assert d["failure_probability"] == result.failure_probability
        assert d["risk_score"] == result.risk_score
        assert d["risk_level"] == result.risk_level

    def test_risk_level_in_dict_is_string(self, fake_artifacts):
        from ml.assessment import assess_machine

        result = assess_machine(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        d = result.to_dict()
        assert isinstance(d["risk_level"], str)
        assert d["risk_level"] in ("NORMAL", "WARNING", "CRITICAL")
