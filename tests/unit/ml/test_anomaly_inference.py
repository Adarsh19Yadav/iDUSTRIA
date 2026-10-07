"""tests/unit/ml/test_anomaly_inference.py — Unit tests for Phase 4 anomaly detection.

Tests cover:
  1.  Artifact loading — pipeline + metadata load without error
  2.  Valid inference — returns AnomalyResult instance
  3.  Score returned — anomaly_score present and in [0, 1]
  4.  Anomaly flag — is_anomaly is bool
  5.  Deterministic output — identical input → identical output
  6.  Invalid type_ → ValueError
  7.  None/NaN numeric input → ValueError
  8.  Missing anomaly_pipeline.joblib → FileNotFoundError
  9.  Missing anomaly_metadata.json → FileNotFoundError
 10.  to_dict() returns all expected keys
 11.  Raw score sign agrees with is_anomaly flag
 12.  Normalised score matches normalisation formula
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
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
def clear_anomaly_cache():
    """Clear the anomaly singleton cache before and after each test."""
    from ml.anomaly_inference import _AnomalyCache

    _AnomalyCache.clear_cache()
    yield
    _AnomalyCache.clear_cache()


@pytest.fixture
def anomaly_artifacts_dir() -> Path:
    """Return path to the real v1 anomaly artifacts."""
    return Path("ml/artifacts/v1")


@pytest.fixture
def fake_anomaly_artifacts(tmp_path, anomaly_artifacts_dir):
    """Copy real anomaly artifacts into a tmp directory for test isolation."""
    dst = tmp_path / "v1"
    dst.mkdir()
    shutil.copy(
        anomaly_artifacts_dir / "anomaly_pipeline.joblib",
        dst / "anomaly_pipeline.joblib",
    )
    shutil.copy(
        anomaly_artifacts_dir / "anomaly_metadata.json",
        dst / "anomaly_metadata.json",
    )
    return dst


# ===========================================================================
# 1. Artifact loading
# ===========================================================================


class TestAnomalyArtifactLoading:
    def test_pipeline_loads_without_error(self, fake_anomaly_artifacts):
        """joblib.load must succeed and return a sklearn Pipeline."""
        import joblib
        from sklearn.pipeline import Pipeline

        pipeline = joblib.load(fake_anomaly_artifacts / "anomaly_pipeline.joblib")
        assert isinstance(pipeline, Pipeline)

    def test_metadata_loads_as_dict(self, fake_anomaly_artifacts):
        """anomaly_metadata.json must parse to a dict with required keys."""
        with open(fake_anomaly_artifacts / "anomaly_metadata.json", encoding="utf-8") as f:
            meta = json.load(f)
        assert isinstance(meta, dict)
        for key in (
            "anomaly_version",
            "algorithm",
            "contamination",
            "feature_columns",
            "train_score_min",
            "train_score_max",
        ):
            assert key in meta, f"Key '{key}' missing from anomaly_metadata.json"

    def test_metadata_algorithm_is_isolation_forest(self, fake_anomaly_artifacts):
        with open(fake_anomaly_artifacts / "anomaly_metadata.json", encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["algorithm"] == "IsolationForest"

    def test_metadata_labels_used_is_false(self, fake_anomaly_artifacts):
        """Anomaly detector must NOT have been trained with failure labels."""
        with open(fake_anomaly_artifacts / "anomaly_metadata.json", encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["labels_used_in_training"] is False

    def test_missing_pipeline_raises_file_not_found(self, tmp_path):
        from ml.anomaly_inference import detect_anomaly

        with pytest.raises(FileNotFoundError, match="anomaly_pipeline"):
            detect_anomaly(**_NORMAL_OBS, artifacts_dir=tmp_path)

    def test_missing_metadata_raises_file_not_found(self, tmp_path, anomaly_artifacts_dir):
        """Only copy the pipeline — no metadata — should raise FileNotFoundError."""
        dst = tmp_path / "partial"
        dst.mkdir()
        shutil.copy(
            anomaly_artifacts_dir / "anomaly_pipeline.joblib",
            dst / "anomaly_pipeline.joblib",
        )
        from ml.anomaly_inference import detect_anomaly

        with pytest.raises(FileNotFoundError, match="anomaly_metadata"):
            detect_anomaly(**_NORMAL_OBS, artifacts_dir=dst)


# ===========================================================================
# 2. Valid inference
# ===========================================================================


class TestAnomalyValidInference:
    def test_returns_anomaly_result(self, fake_anomaly_artifacts):
        from ml.anomaly_inference import AnomalyResult, detect_anomaly

        result = detect_anomaly(**_NORMAL_OBS, artifacts_dir=fake_anomaly_artifacts)
        assert isinstance(result, AnomalyResult)

    def test_result_has_all_fields(self, fake_anomaly_artifacts):
        from ml.anomaly_inference import detect_anomaly

        result = detect_anomaly(**_NORMAL_OBS, artifacts_dir=fake_anomaly_artifacts)
        assert hasattr(result, "anomaly_score")
        assert hasattr(result, "is_anomaly")
        assert hasattr(result, "raw_score")
        assert hasattr(result, "anomaly_version")

    def test_anomaly_version_matches_metadata(self, fake_anomaly_artifacts):
        from ml.anomaly_inference import detect_anomaly

        with open(fake_anomaly_artifacts / "anomaly_metadata.json", encoding="utf-8") as f:
            meta = json.load(f)
        result = detect_anomaly(**_NORMAL_OBS, artifacts_dir=fake_anomaly_artifacts)
        assert result.anomaly_version == meta["anomaly_version"]


# ===========================================================================
# 3. Score in [0, 1]
# ===========================================================================


class TestAnomalyScoreRange:
    @pytest.mark.parametrize(
        "obs",
        [
            # Normal conditions
            dict(
                air_temp_k=300.0,
                process_temp_k=310.0,
                rotational_speed_rpm=1500,
                torque_nm=40.0,
                tool_wear_min=100,
                type_="M",
            ),
            # High-stress conditions
            dict(
                air_temp_k=304.0,
                process_temp_k=313.0,
                rotational_speed_rpm=1200,
                torque_nm=70.0,
                tool_wear_min=240,
                type_="L",
            ),
            # Low-wear conditions
            dict(
                air_temp_k=297.0,
                process_temp_k=307.0,
                rotational_speed_rpm=2000,
                torque_nm=20.0,
                tool_wear_min=0,
                type_="H",
            ),
        ],
    )
    def test_anomaly_score_in_unit_interval(self, obs, fake_anomaly_artifacts):
        """anomaly_score must always be in [0.0, 1.0]."""
        from ml.anomaly_inference import detect_anomaly

        result = detect_anomaly(**obs, artifacts_dir=fake_anomaly_artifacts)
        assert 0.0 <= result.anomaly_score <= 1.0


# ===========================================================================
# 4. Anomaly flag is bool
# ===========================================================================


class TestAnomalyFlag:
    def test_is_anomaly_is_bool(self, fake_anomaly_artifacts):
        from ml.anomaly_inference import detect_anomaly

        result = detect_anomaly(**_NORMAL_OBS, artifacts_dir=fake_anomaly_artifacts)
        assert isinstance(result.is_anomaly, bool)

    def test_raw_score_sign_consistent_with_flag(self, fake_anomaly_artifacts):
        """When is_anomaly=True, raw_score should be < 0 (sklearn convention)."""
        from ml.anomaly_inference import detect_anomaly

        result = detect_anomaly(**_NORMAL_OBS, artifacts_dir=fake_anomaly_artifacts)
        if result.is_anomaly:
            assert result.raw_score < 0
        else:
            assert result.raw_score >= 0


# ===========================================================================
# 5. Deterministic output
# ===========================================================================


class TestAnomalyDeterministic:
    def test_same_input_gives_same_output(self, fake_anomaly_artifacts):
        """Calling detect_anomaly twice with the same input must return identical results."""
        from ml.anomaly_inference import detect_anomaly

        r1 = detect_anomaly(**_NORMAL_OBS, artifacts_dir=fake_anomaly_artifacts)
        r2 = detect_anomaly(**_NORMAL_OBS, artifacts_dir=fake_anomaly_artifacts)
        assert r1.anomaly_score == r2.anomaly_score
        assert r1.is_anomaly == r2.is_anomaly
        assert r1.raw_score == r2.raw_score


# ===========================================================================
# 6. Invalid type_ → ValueError
# ===========================================================================


class TestAnomalyInvalidType:
    @pytest.mark.parametrize("bad_type", ["X", "Z", "l", "m", "h", "", "LMH", "1"])
    def test_invalid_type_raises_value_error(self, bad_type, fake_anomaly_artifacts):
        from ml.anomaly_inference import detect_anomaly

        obs = dict(_NORMAL_OBS)
        obs["type_"] = bad_type
        with pytest.raises(ValueError, match="type_"):
            detect_anomaly(**obs, artifacts_dir=fake_anomaly_artifacts)

    def test_all_valid_types_accepted(self, fake_anomaly_artifacts):
        from ml.anomaly_inference import detect_anomaly

        for t in ("L", "M", "H"):
            obs = dict(_NORMAL_OBS)
            obs["type_"] = t
            result = detect_anomaly(**obs, artifacts_dir=fake_anomaly_artifacts)
            assert 0.0 <= result.anomaly_score <= 1.0


# ===========================================================================
# 7. None/NaN numeric input → ValueError
# ===========================================================================


class TestAnomalyMissingInputs:
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
    def test_none_or_nan_raises_value_error(self, field, value, fake_anomaly_artifacts):
        from ml.anomaly_inference import detect_anomaly

        obs = dict(_NORMAL_OBS)
        obs[field] = value
        with pytest.raises(ValueError, match=field):
            detect_anomaly(**obs, artifacts_dir=fake_anomaly_artifacts)


# ===========================================================================
# 8. to_dict() has all expected keys
# ===========================================================================


class TestAnomalyToDict:
    def test_to_dict_returns_all_keys(self, fake_anomaly_artifacts):
        from ml.anomaly_inference import detect_anomaly

        result = detect_anomaly(**_NORMAL_OBS, artifacts_dir=fake_anomaly_artifacts)
        d = result.to_dict()
        assert isinstance(d, dict)
        for key in ("anomaly_score", "is_anomaly", "raw_score", "anomaly_version"):
            assert key in d

    def test_to_dict_values_match_result(self, fake_anomaly_artifacts):
        from ml.anomaly_inference import detect_anomaly

        result = detect_anomaly(**_NORMAL_OBS, artifacts_dir=fake_anomaly_artifacts)
        d = result.to_dict()
        assert d["anomaly_score"] == result.anomaly_score
        assert d["is_anomaly"] == result.is_anomaly
        assert d["raw_score"] == result.raw_score


# ===========================================================================
# 9. Normalisation consistency
# ===========================================================================


class TestAnomalyNormalisation:
    def test_normalise_score_zero_for_most_normal(self):
        """A raw score equal to train_score_max (most normal) should give ≈0."""
        from ml.anomaly_inference import _normalise_score

        # raw_score = train_score_max → negated = -train_score_max = min_bound → result = 0
        score = _normalise_score(
            raw_score=0.17,
            train_score_min=-0.12,
            train_score_max=0.17,
        )
        assert abs(score - 0.0) < 1e-6

    def test_normalise_score_one_for_most_anomalous(self):
        """A raw score equal to train_score_min (most anomalous) should give ≈1."""
        from ml.anomaly_inference import _normalise_score

        score = _normalise_score(
            raw_score=-0.12,
            train_score_min=-0.12,
            train_score_max=0.17,
        )
        assert abs(score - 1.0) < 1e-6

    def test_normalise_score_clips_outside_training_range(self):
        """Scores more extreme than the training range must be clipped to [0, 1]."""
        from ml.anomaly_inference import _normalise_score

        # Beyond most anomalous → still capped at 1
        assert _normalise_score(-0.99, -0.12, 0.17) == 1.0
        # Beyond most normal → still floored at 0
        assert _normalise_score(0.99, -0.12, 0.17) == 0.0
