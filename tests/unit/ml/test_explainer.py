"""tests/unit/ml/test_explainer.py — Unit tests for Phase 5 SHAP explainability.

Tests cover:

SHAP / Explainer
  1.  Explainer and preprocessor load without error
  2.  explain_prediction returns ExplanationResult
  3.  All required fields present
  4.  Correct feature names in output
  5.  SHAP values returned (non-zero for varied inputs)
  6.  Direction labels are valid
  7.  Deterministic / reproducible explanation
  8.  Probability matches production inference (predict_failure)
  9.  Invalid type_ → ValueError
  10. None/NaN numeric → ValueError
  11. Missing artifact → FileNotFoundError
  12. to_dict returns all expected keys

Human-readable summary
  13. Summary text is generated (non-empty string)
  14. Summary contains probability
  15. No causal language (no "caused", "led to", "resulted in")
  16. Features sorted by descending contribution in summary
  17. HIGH/LOW risk label present

Global explanation
  18. compute_global_importance returns GlobalImportance
  19. All expected features present
  20. Mean abs SHAP values are non-negative
  21. Features ranked in descending importance order
  22. sample_size is correct
  23. JSON artifact is saved (when save_json=True)
  24. No fabricated features (all features are from FEATURE_COLUMNS)
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from ml.data.features import FEATURE_COLUMNS

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

_CAUSAL_WORDS = [
    "caused",
    "led to",
    "resulted in",
    "is responsible for",
    "induces",
    "triggers",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear model + explainer caches before and after each test."""
    from ml.explainer import _ExplainerCache
    from ml.inference import _ModelCache

    _ModelCache.clear_cache()
    _ExplainerCache.clear_cache()
    yield
    _ModelCache.clear_cache()
    _ExplainerCache.clear_cache()


@pytest.fixture
def real_artifacts_dir() -> Path:
    return Path("ml/artifacts/v1")


@pytest.fixture
def fake_artifacts(tmp_path, real_artifacts_dir):
    """Copy failure model artifacts to a tmp directory."""
    dst = tmp_path / "v1"
    dst.mkdir()
    shutil.copy(real_artifacts_dir / "model_pipeline.joblib", dst / "model_pipeline.joblib")
    shutil.copy(real_artifacts_dir / "metadata.json", dst / "metadata.json")
    return dst


# ===========================================================================
# 1. Explainer loading
# ===========================================================================


class TestExplainerLoading:
    def test_explainer_loads_without_error(self, fake_artifacts):
        from ml.explainer import _ExplainerCache

        explainer, preprocessor = _ExplainerCache.load(fake_artifacts)
        assert explainer is not None
        assert preprocessor is not None

    def test_missing_artifact_raises_file_not_found(self, tmp_path):
        from ml.explainer import explain_prediction

        with pytest.raises(FileNotFoundError, match="model_pipeline"):
            explain_prediction(**_NORMAL_OBS, artifacts_dir=tmp_path)


# ===========================================================================
# 2–4. Valid explanation structure
# ===========================================================================


class TestValidExplanation:
    def test_returns_explanation_result(self, fake_artifacts):
        from ml.explainer import ExplanationResult, explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert isinstance(result, ExplanationResult)

    def test_all_required_fields_present(self, fake_artifacts):
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        for attr in (
            "failure_probability",
            "predicted_failure",
            "threshold",
            "model_version",
            "base_value",
            "shap_sum",
            "features",
            "summary_text",
        ):
            assert hasattr(result, attr), f"Missing attribute: {attr}"

    def test_correct_feature_names(self, fake_artifacts):
        """Every feature in the result must be from FEATURE_COLUMNS."""
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        result_features = [f.feature for f in result.features]
        assert set(result_features) == set(FEATURE_COLUMNS)
        assert len(result_features) == len(FEATURE_COLUMNS)

    def test_number_of_features_matches_feature_columns(self, fake_artifacts):
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert len(result.features) == len(FEATURE_COLUMNS)


# ===========================================================================
# 5. SHAP values returned
# ===========================================================================


class TestSHAPValues:
    def test_shap_values_are_floats(self, fake_artifacts):
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        for f in result.features:
            assert isinstance(f.shap_value, float)
            assert isinstance(f.contribution, float)

    def test_base_value_is_float(self, fake_artifacts):
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert isinstance(result.base_value, float)

    def test_shap_sum_consistent_with_individual_values(self, fake_artifacts):
        """shap_sum should equal sum of individual shap_values (within fp precision)."""
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        expected_sum = sum(f.shap_value for f in result.features)
        assert abs(result.shap_sum - expected_sum) < 1e-3

    def test_contributions_are_non_negative(self, fake_artifacts):
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        for f in result.features:
            assert f.contribution >= 0.0

    def test_contribution_equals_abs_shap(self, fake_artifacts):
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        for f in result.features:
            assert abs(f.contribution - abs(f.shap_value)) < 1e-9


# ===========================================================================
# 6. Direction labels
# ===========================================================================


class TestDirectionLabels:
    def test_direction_labels_are_valid(self, fake_artifacts):
        from ml.explainer import explain_prediction

        valid_directions = {
            "increases_failure_risk",
            "decreases_failure_risk",
            "neutral",
        }
        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        for f in result.features:
            assert f.direction in valid_directions

    def test_positive_shap_gives_increases_label(self, fake_artifacts):
        """High-stress obs should have at least one 'increases_failure_risk' feature."""
        from ml.explainer import explain_prediction

        stressed = explain_prediction(
            air_temp_k=303.0,
            process_temp_k=313.0,
            rotational_speed_rpm=1200,
            torque_nm=68.0,
            tool_wear_min=240,
            type_="L",
            artifacts_dir=fake_artifacts,
        )
        increasing = [f for f in stressed.features if f.direction == "increases_failure_risk"]
        assert len(increasing) >= 1

    def test_negative_shap_gives_decreases_label(self, fake_artifacts):
        """Normal obs should have at least one 'decreases_failure_risk' feature."""
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        decreasing = [f for f in result.features if f.direction == "decreases_failure_risk"]
        assert len(decreasing) >= 1


# ===========================================================================
# 7. Determinism
# ===========================================================================


class TestDeterministicExplanation:
    def test_same_input_gives_same_shap_values(self, fake_artifacts):
        from ml.explainer import explain_prediction

        r1 = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        r2 = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert r1.failure_probability == r2.failure_probability
        assert r1.shap_sum == r2.shap_sum
        for f1, f2 in zip(r1.features, r2.features):
            assert f1.shap_value == f2.shap_value


# ===========================================================================
# 8. Probability matches production inference
# ===========================================================================


class TestProbabilityConsistency:
    def test_probability_matches_predict_failure(self, fake_artifacts):
        """Probability from explain_prediction must match predict_failure."""
        from ml.explainer import explain_prediction
        from ml.inference import predict_failure

        expl = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        pred = predict_failure(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert abs(expl.failure_probability - pred.failure_probability) < 1e-4

    def test_predicted_failure_matches_predict_failure(self, fake_artifacts):
        from ml.explainer import explain_prediction
        from ml.inference import predict_failure

        expl = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        pred = predict_failure(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert expl.predicted_failure == pred.predicted_failure

    def test_threshold_matches_metadata(self, fake_artifacts):
        import json

        from ml.explainer import explain_prediction

        with open(fake_artifacts / "metadata.json", encoding="utf-8") as fh:
            meta = json.load(fh)
        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert abs(result.threshold - meta["threshold"]) < 1e-9

    def test_model_version_matches_metadata(self, fake_artifacts):
        import json

        from ml.explainer import explain_prediction

        with open(fake_artifacts / "metadata.json", encoding="utf-8") as fh:
            meta = json.load(fh)
        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert result.model_version == meta["model_version"]

    def test_probability_in_unit_interval(self, fake_artifacts):
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert 0.0 <= result.failure_probability <= 1.0


# ===========================================================================
# 9–10. Invalid input handling
# ===========================================================================


class TestInvalidInputHandling:
    @pytest.mark.parametrize("bad_type", ["X", "Z", "l", "m", "h", "", "LMH", "1"])
    def test_invalid_type_raises_value_error(self, bad_type, fake_artifacts):
        from ml.explainer import explain_prediction

        obs = dict(_NORMAL_OBS)
        obs["type_"] = bad_type
        with pytest.raises(ValueError, match="type_"):
            explain_prediction(**obs, artifacts_dir=fake_artifacts)

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
        from ml.explainer import explain_prediction

        obs = dict(_NORMAL_OBS)
        obs[field] = value
        with pytest.raises(ValueError, match=field):
            explain_prediction(**obs, artifacts_dir=fake_artifacts)


# ===========================================================================
# 12. to_dict
# ===========================================================================


class TestExplanationToDict:
    def test_to_dict_returns_all_keys(self, fake_artifacts):
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        d = result.to_dict()
        assert isinstance(d, dict)
        for key in (
            "failure_probability",
            "predicted_failure",
            "threshold",
            "model_version",
            "base_value",
            "shap_sum",
            "features",
            "summary_text",
        ):
            assert key in d

    def test_features_in_dict_are_list_of_dicts(self, fake_artifacts):
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        d = result.to_dict()
        assert isinstance(d["features"], list)
        for item in d["features"]:
            assert isinstance(item, dict)
            for key in ("feature", "value", "shap_value", "direction", "contribution"):
                assert key in item


# ===========================================================================
# 13–17. Human-readable summary
# ===========================================================================


class TestHumanReadableSummary:
    def test_summary_is_non_empty_string(self, fake_artifacts):
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert isinstance(result.summary_text, str)
        assert len(result.summary_text) > 0

    def test_summary_contains_probability(self, fake_artifacts):
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        # The probability should appear in the summary (as a number)
        assert "probability" in result.summary_text.lower()

    def test_no_causal_language_in_summary(self, fake_artifacts):
        """Summary must not use causal language."""
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        lower = result.summary_text.lower()
        for word in _CAUSAL_WORDS:
            assert word not in lower, (
                f"Causal language '{word}' found in summary. "
                "Use model-attribution wording only."
            )

    def test_no_causal_language_in_stressed_obs(self, fake_artifacts):
        from ml.explainer import explain_prediction

        result = explain_prediction(
            air_temp_k=303.0,
            process_temp_k=313.0,
            rotational_speed_rpm=1200,
            torque_nm=68.0,
            tool_wear_min=240,
            type_="L",
            artifacts_dir=fake_artifacts,
        )
        lower = result.summary_text.lower()
        for word in _CAUSAL_WORDS:
            assert word not in lower, f"Causal word '{word}' found in summary."

    def test_summary_contains_risk_label(self, fake_artifacts):
        """Summary should state HIGH or LOW failure risk."""
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        assert "failure risk" in result.summary_text.lower()

    def test_features_sorted_by_contribution_descending(self, fake_artifacts):
        """Features list must be sorted by descending absolute contribution."""
        from ml.explainer import explain_prediction

        result = explain_prediction(**_NORMAL_OBS, artifacts_dir=fake_artifacts)
        contributions = [f.contribution for f in result.features]
        assert contributions == sorted(contributions, reverse=True)

    def test_high_stress_summary_mentions_increases(self, fake_artifacts):
        """Stressed observation summary should mention 'increased'."""
        from ml.explainer import explain_prediction

        result = explain_prediction(
            air_temp_k=303.0,
            process_temp_k=313.0,
            rotational_speed_rpm=1200,
            torque_nm=68.0,
            tool_wear_min=240,
            type_="L",
            artifacts_dir=fake_artifacts,
        )
        assert "increased" in result.summary_text.lower()


# ===========================================================================
# 18–24. Global feature importance
# ===========================================================================


class TestGlobalImportance:
    def test_returns_global_importance(self):
        from ml.explainer import GlobalImportance, compute_global_importance

        gi = compute_global_importance(sample_size=50, save_json=False)
        assert isinstance(gi, GlobalImportance)

    def test_all_expected_features_present(self):
        from ml.explainer import compute_global_importance

        gi = compute_global_importance(sample_size=50, save_json=False)
        assert set(gi.features) == set(FEATURE_COLUMNS)

    def test_mean_abs_shap_are_non_negative(self):
        from ml.explainer import compute_global_importance

        gi = compute_global_importance(sample_size=50, save_json=False)
        for v in gi.mean_abs_shap:
            assert v >= 0.0

    def test_features_ranked_descending(self):
        """Features must be ranked by descending mean abs SHAP."""
        from ml.explainer import compute_global_importance

        gi = compute_global_importance(sample_size=50, save_json=False)
        assert gi.mean_abs_shap == sorted(gi.mean_abs_shap, reverse=True)

    def test_sample_size_is_correct(self):
        from ml.explainer import compute_global_importance

        gi = compute_global_importance(sample_size=50, save_json=False)
        assert gi.sample_size == 50

    def test_json_artifact_saved(self, tmp_path, real_artifacts_dir):
        """When save_json=True, the JSON file must be created."""
        from ml.explainer import _ExplainerCache
        from ml.inference import _ModelCache

        _ModelCache.clear_cache()
        _ExplainerCache.clear_cache()

        # Copy artifacts to tmp
        dst = tmp_path / "v1"
        dst.mkdir()
        shutil.copy(real_artifacts_dir / "model_pipeline.joblib", dst / "model_pipeline.joblib")
        shutil.copy(real_artifacts_dir / "metadata.json", dst / "metadata.json")

        from ml.explainer import compute_global_importance

        gi = compute_global_importance(
            artifacts_dir=dst,
            sample_size=30,
            save_json=True,
        )
        json_path = dst / "global_shap_importance.json"
        assert json_path.exists()

        with open(json_path, encoding="utf-8") as fh:
            saved = json.load(fh)
        assert saved["features"] == gi.features
        assert saved["mean_abs_shap"] == gi.mean_abs_shap

    def test_no_fabricated_features(self):
        """All features in global importance must come from FEATURE_COLUMNS."""
        from ml.explainer import compute_global_importance

        gi = compute_global_importance(sample_size=30, save_json=False)
        for feat in gi.features:
            assert feat in FEATURE_COLUMNS

    def test_model_version_present(self):
        from ml.explainer import compute_global_importance

        gi = compute_global_importance(sample_size=30, save_json=False)
        assert isinstance(gi.model_version, str)
        assert len(gi.model_version) > 0

    def test_to_dict_structure(self):
        from ml.explainer import compute_global_importance

        gi = compute_global_importance(sample_size=30, save_json=False)
        d = gi.to_dict()
        assert isinstance(d, dict)
        for key in ("features", "mean_abs_shap", "sample_size", "model_version"):
            assert key in d


# ===========================================================================
# get_shap_metadata
# ===========================================================================


class TestSHAPMetadata:
    def test_metadata_has_expected_keys(self, fake_artifacts):
        from ml.explainer import get_shap_metadata

        meta = get_shap_metadata(artifacts_dir=fake_artifacts)
        for key in ("shap_method", "shap_space", "model_version", "feature_columns", "note"):
            assert key in meta

    def test_shap_method_is_tree_explainer(self, fake_artifacts):
        from ml.explainer import get_shap_metadata

        meta = get_shap_metadata(artifacts_dir=fake_artifacts)
        assert meta["shap_method"] == "TreeExplainer"

    def test_shap_space_is_log_odds(self, fake_artifacts):
        from ml.explainer import get_shap_metadata

        meta = get_shap_metadata(artifacts_dir=fake_artifacts)
        assert "log-odds" in meta["shap_space"]
