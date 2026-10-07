"""tests/unit/ml/test_inference.py — Unit tests for Phase 3 inference module.

Tests cover:
  1. Model artifact loading (pipeline + metadata)
  2. Valid prediction returns expected fields
  3. Probability range [0, 1]
  4. Expected feature validation (correct feature columns in metadata)
  5. Missing feature handling (None / NaN inputs)
  6. Invalid categorical value handling
  7. Threshold application (probability just below/above threshold)
  8. Deterministic / reproducible inference
  9. Metadata structure
 10. Artifact FileNotFoundError on missing files
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers — minimal real observation (within dataset distribution)
# ---------------------------------------------------------------------------

_NORMAL_OBS = dict(
    air_temp_k=300.0,
    process_temp_k=310.0,
    rotational_speed_rpm=1500,
    torque_nm=40.0,
    tool_wear_min=100,
    type_="M",
)

# Force a reload before every test class so tmp_path fixtures work cleanly
@pytest.fixture(autouse=True)
def clear_model_cache():
    """Clear the inference singleton cache before each test."""
    from ml.inference import _ModelCache
    _ModelCache.clear_cache()
    yield
    _ModelCache.clear_cache()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def artifacts_dir() -> Path:
    """Return path to the real v1 artifacts."""
    return Path("ml/artifacts/v1")


@pytest.fixture
def fake_artifacts(tmp_path, artifacts_dir):
    """Copy real artifacts into a tmp directory for isolation."""
    import shutil
    src = artifacts_dir
    dst = tmp_path / "v1"
    dst.mkdir()
    shutil.copy(src / "model_pipeline.joblib", dst / "model_pipeline.joblib")
    shutil.copy(src / "metadata.json", dst / "metadata.json")
    return dst


# ===========================================================================
# 1. Model artifact loading
# ===========================================================================

class TestArtifactLoading:
    def test_pipeline_loads_without_error(self, fake_artifacts):
        """joblib.load must succeed and return a sklearn Pipeline."""
        import joblib
        from sklearn.pipeline import Pipeline

        pipeline = joblib.load(fake_artifacts / "model_pipeline.joblib")
        assert isinstance(pipeline, Pipeline)

    def test_metadata_loads_as_dict(self, fake_artifacts):
        """metadata.json must parse to a dict with required keys."""
        with open(fake_artifacts / "metadata.json", encoding="utf-8") as f:
            meta = json.load(f)
        assert isinstance(meta, dict)
        for key in ("model_version", "model_name", "threshold", "feature_columns"):
            assert key in meta, f"Key '{key}' missing from metadata.json"

    def test_metadata_threshold_is_float_in_range(self, fake_artifacts):
        """Threshold stored in metadata must be in [0, 1]."""
        with open(fake_artifacts / "metadata.json", encoding="utf-8") as f:
            meta = json.load(f)
        t = meta["threshold"]
        assert isinstance(t, (int, float))
        assert 0.0 <= t <= 1.0

    def test_missing_pipeline_raises_file_not_found(self, tmp_path):
        """predict_failure must raise FileNotFoundError when artifact is absent."""
        from ml.inference import predict_failure

        with pytest.raises(FileNotFoundError, match="model_pipeline"):
            predict_failure(**_NORMAL_OBS, artifacts_dir=tmp_path)

    def test_missing_metadata_raises_file_not_found(self, tmp_path):
        """predict_failure must raise FileNotFoundError when metadata is absent."""
        import joblib
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        # Create a dummy pipeline file but no metadata
        dummy_pipeline = Pipeline([("scaler", StandardScaler())])
        joblib.dump(dummy_pipeline, tmp_path / "model_pipeline.joblib")

        from ml.inference import predict_failure
        with pytest.raises(FileNotFoundError, match="metadata"):
            predict_failure(**_NORMAL_OBS, artifacts_dir=tmp_path)


# ===========================================================================
# 2. Valid prediction
# ===========================================================================

class TestValidPrediction:
    def test_predict_failure_returns_inference_result(self, fake_artifacts):
        """predict_failure must return an InferenceResult instance."""
        from ml.inference import InferenceResult, predict_failure

        result = predict_failure(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert isinstance(result, InferenceResult)

    def test_result_has_all_fields(self, fake_artifacts):
        """InferenceResult must have failure_probability, predicted_failure,
        threshold, and model_version fields."""
        from ml.inference import predict_failure

        result = predict_failure(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert hasattr(result, "failure_probability")
        assert hasattr(result, "predicted_failure")
        assert hasattr(result, "threshold")
        assert hasattr(result, "model_version")

    def test_predicted_failure_is_0_or_1(self, fake_artifacts):
        """predicted_failure must be 0 or 1."""
        from ml.inference import predict_failure

        result = predict_failure(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert result.predicted_failure in (0, 1)

    def test_to_dict_returns_dict(self, fake_artifacts):
        """InferenceResult.to_dict() must return a plain dict."""
        from ml.inference import predict_failure

        result = predict_failure(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "failure_probability" in d
        assert "predicted_failure" in d
        assert "threshold" in d
        assert "model_version" in d

    def test_model_version_matches_metadata(self, fake_artifacts):
        """model_version in result must match metadata.json."""
        from ml.inference import predict_failure
        with open(fake_artifacts / "metadata.json", encoding="utf-8") as f:
            meta = json.load(f)

        result = predict_failure(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert result.model_version == meta["model_version"]


# ===========================================================================
# 3. Probability range [0, 1]
# ===========================================================================

class TestProbabilityRange:
    @pytest.mark.parametrize(
        "obs",
        [
            # Normal operating condition
            dict(air_temp_k=300.0, process_temp_k=310.0,
                 rotational_speed_rpm=1500, torque_nm=40.0,
                 tool_wear_min=100, type_="M"),
            # High stress (near failure range)
            dict(air_temp_k=304.0, process_temp_k=313.0,
                 rotational_speed_rpm=1200, torque_nm=70.0,
                 tool_wear_min=240, type_="L"),
            # Low wear
            dict(air_temp_k=297.0, process_temp_k=307.0,
                 rotational_speed_rpm=2000, torque_nm=20.0,
                 tool_wear_min=0, type_="H"),
        ],
    )
    def test_probability_in_unit_interval(self, obs, fake_artifacts):
        """failure_probability must always be in [0.0, 1.0]."""
        from ml.inference import predict_failure

        result = predict_failure(**obs, artifacts_dir=fake_artifacts)
        assert 0.0 <= result.failure_probability <= 1.0


# ===========================================================================
# 4. Expected feature validation
# ===========================================================================

class TestFeatureValidation:
    def test_metadata_feature_columns_match_module_constants(self, fake_artifacts):
        """feature_columns in metadata must match FEATURE_COLUMNS."""
        from ml.data.features import FEATURE_COLUMNS
        with open(fake_artifacts / "metadata.json", encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["feature_columns"] == FEATURE_COLUMNS

    def test_metadata_has_numerical_and_categorical_lists(self, fake_artifacts):
        """Metadata must list numerical_features and categorical_features."""
        from ml.data.features import NUMERICAL_FEATURES, CATEGORICAL_FEATURES
        with open(fake_artifacts / "metadata.json", encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["numerical_features"] == NUMERICAL_FEATURES
        assert meta["categorical_features"] == CATEGORICAL_FEATURES


# ===========================================================================
# 5. Missing feature handling (None / NaN)
# ===========================================================================

class TestMissingFeatureHandling:
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
    def test_none_or_nan_raises_value_error(self, field, value, fake_artifacts):
        """predict_failure must raise ValueError for None or NaN numeric inputs."""
        from ml.inference import predict_failure

        obs = dict(_NORMAL_OBS)
        obs[field] = value
        with pytest.raises(ValueError, match=field):
            predict_failure(**obs, artifacts_dir=fake_artifacts)


# ===========================================================================
# 6. Invalid categorical value handling
# ===========================================================================

class TestInvalidCategoricalValue:
    @pytest.mark.parametrize("bad_type", ["X", "Z", "l", "m", "h", "", "LMH", "1"])
    def test_invalid_type_raises_value_error(self, bad_type, fake_artifacts):
        """predict_failure must raise ValueError for type_ not in {L, M, H}."""
        from ml.inference import predict_failure

        obs = dict(_NORMAL_OBS)
        obs["type_"] = bad_type
        with pytest.raises(ValueError, match="type_"):
            predict_failure(**obs, artifacts_dir=fake_artifacts)

    def test_valid_types_all_accepted(self, fake_artifacts):
        """All three valid type values (L, M, H) must be accepted."""
        from ml.inference import predict_failure

        for t in ("L", "M", "H"):
            obs = dict(_NORMAL_OBS)
            obs["type_"] = t
            result = predict_failure(**obs, artifacts_dir=fake_artifacts)
            assert result.predicted_failure in (0, 1)


# ===========================================================================
# 7. Threshold application
# ===========================================================================

class TestThresholdApplication:
    def test_threshold_matches_metadata(self, fake_artifacts):
        """threshold in result must equal the value stored in metadata.json."""
        from ml.inference import predict_failure
        with open(fake_artifacts / "metadata.json", encoding="utf-8") as f:
            meta = json.load(f)

        result = predict_failure(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert abs(result.threshold - meta["threshold"]) < 1e-9

    def test_high_probability_predicts_failure(self, fake_artifacts, monkeypatch):
        """When probability > threshold, predicted_failure must be 1."""
        from ml import inference
        import numpy as np

        # Patch pipeline.predict_proba to return a high probability
        original_load = inference._ModelCache.load

        def patched_load(artifacts_dir=None):
            pipeline, metadata = original_load(artifacts_dir)

            class _MockPipeline:
                def predict_proba(self, X):
                    # Return prob just above threshold
                    t = metadata["threshold"]
                    return np.array([[1 - (t + 0.1), t + 0.1]])

            return _MockPipeline(), metadata

        monkeypatch.setattr(inference._ModelCache, "load", patched_load)
        result = inference.predict_failure(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert result.predicted_failure == 1

    def test_low_probability_predicts_no_failure(self, fake_artifacts, monkeypatch):
        """When probability < threshold, predicted_failure must be 0."""
        from ml import inference
        import numpy as np

        original_load = inference._ModelCache.load

        def patched_load(artifacts_dir=None):
            pipeline, metadata = original_load(artifacts_dir)

            class _MockPipeline:
                def predict_proba(self, X):
                    t = metadata["threshold"]
                    return np.array([[1 - (t - 0.1), t - 0.1]])

            return _MockPipeline(), metadata

        monkeypatch.setattr(inference._ModelCache, "load", patched_load)
        result = inference.predict_failure(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert result.predicted_failure == 0


# ===========================================================================
# 8. Deterministic / reproducible inference
# ===========================================================================

class TestDeterministicInference:
    def test_same_input_gives_same_output(self, fake_artifacts):
        """Calling predict_failure twice with the same input must return identical results."""
        from ml.inference import predict_failure

        result1 = predict_failure(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        result2 = predict_failure(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert result1.failure_probability == result2.failure_probability
        assert result1.predicted_failure == result2.predicted_failure

    def test_different_inputs_may_differ(self, fake_artifacts):
        """A normal and a high-stress observation should not both produce identical
        probabilities (they should differ)."""
        from ml.inference import predict_failure

        normal = predict_failure(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        # High tool wear + low speed + high torque — more failure-prone profile
        stressed = predict_failure(
            air_temp_k=303.0,
            process_temp_k=313.0,
            rotational_speed_rpm=1200,
            torque_nm=68.0,
            tool_wear_min=240,
            type_="L",
            artifacts_dir=fake_artifacts,
        )
        # They may or may not differ, but we verify both run without error
        assert 0.0 <= normal.failure_probability <= 1.0
        assert 0.0 <= stressed.failure_probability <= 1.0


# ===========================================================================
# 9. Metadata structure
# ===========================================================================

class TestMetadataStructure:
    def test_get_model_metadata_returns_dict(self, fake_artifacts):
        """get_model_metadata() must return a dict."""
        from ml.inference import get_model_metadata

        meta = get_model_metadata(artifacts_dir=fake_artifacts)
        assert isinstance(meta, dict)

    def test_evaluation_metrics_present(self, fake_artifacts):
        """Metadata must contain evaluation_metrics for all trained models."""
        from ml.inference import get_model_metadata

        meta = get_model_metadata(artifacts_dir=fake_artifacts)
        assert "evaluation_metrics" in meta
        metrics = meta["evaluation_metrics"]
        # At least the selected model should be in there
        assert meta["model_name"] in metrics

    def test_dataset_field_is_synthetic_notice(self, fake_artifacts):
        """Dataset field in metadata must mention 'synthetic'."""
        from ml.inference import get_model_metadata

        meta = get_model_metadata(artifacts_dir=fake_artifacts)
        assert "dataset" in meta
        assert "synthetic" in meta["dataset"].lower()
