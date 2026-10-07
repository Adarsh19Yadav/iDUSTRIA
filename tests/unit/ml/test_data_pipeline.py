"""tests/unit/ml/test_data_pipeline.py — Unit tests for the Phase 2 data pipeline.

Tests cover:
  - Dataset loading (happy path)
  - Missing dataset handling (FileNotFoundError)
  - Required-column validation (ValueError on bad CSV)
  - Target validation
  - Preprocessing pipeline
  - Leakage exclusion
  - Reproducible train/test split
  - Invalid input handling
"""

from __future__ import annotations

import io
import textwrap
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Minimal valid dataset that mirrors the real AI4I 2020 schema
_VALID_CSV = textwrap.dedent(
    """\
    UDI,Product ID,Type,Air temperature [K],Process temperature [K],Rotational speed [rpm],Torque [Nm],Tool wear [min],Machine failure,TWF,HDF,PWF,OSF,RNF
    1,M14860,M,298.1,308.6,1551,42.8,0,0,0,0,0,0,0
    2,L47181,L,298.2,308.7,1408,46.3,3,0,0,0,0,0,0
    3,H11111,H,299.0,309.0,1600,38.0,10,1,1,0,0,0,0
    4,L47182,L,298.1,308.5,1498,49.4,5,0,0,0,0,0,0
    5,M14861,M,301.0,311.0,1700,35.0,80,1,0,1,0,0,0
    """
)


@pytest.fixture
def valid_df() -> pd.DataFrame:
    """Return a minimal valid DataFrame matching the AI4I 2020 schema."""
    return pd.read_csv(io.StringIO(_VALID_CSV))


@pytest.fixture
def real_csv_path() -> Path:
    """Path to the actual raw CSV (may or may not exist)."""
    return Path("data/raw/ai4i2020.csv")


# ---------------------------------------------------------------------------
# 1. Dataset loading — happy path
# ---------------------------------------------------------------------------


class TestLoader:
    def test_load_raw_returns_dataframe(self, tmp_path):
        """load_raw() returns a DataFrame when the file exists."""
        from ml.data.loader import load_raw, REQUIRED_COLUMNS

        csv_file = tmp_path / "ai4i2020.csv"
        csv_file.write_text(_VALID_CSV, encoding="utf-8")

        df = load_raw(csv_file)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert len(df.columns) == 14

    def test_load_raw_preserves_all_columns(self, tmp_path):
        """load_raw() must not drop or rename any original column."""
        from ml.data.loader import load_raw, REQUIRED_COLUMNS

        csv_file = tmp_path / "ai4i2020.csv"
        csv_file.write_text(_VALID_CSV, encoding="utf-8")

        df = load_raw(csv_file)
        for col in REQUIRED_COLUMNS:
            assert col in df.columns, f"Column '{col}' missing from loaded dataframe"

    def test_load_raw_does_not_modify_data(self, tmp_path):
        """load_raw() must preserve raw values without transformation."""
        from ml.data.loader import load_raw

        csv_file = tmp_path / "ai4i2020.csv"
        csv_file.write_text(_VALID_CSV, encoding="utf-8")

        df = load_raw(csv_file)
        assert df.iloc[0]["UDI"] == 1
        assert df.iloc[0]["Type"] == "M"
        assert df.iloc[0]["Machine failure"] == 0
        assert df.iloc[2]["Machine failure"] == 1


# ---------------------------------------------------------------------------
# 2. Missing dataset handling
# ---------------------------------------------------------------------------


class TestMissingDataset:
    def test_missing_file_raises_file_not_found(self, tmp_path):
        """load_raw() raises FileNotFoundError when the CSV is absent."""
        from ml.data.loader import load_raw

        nonexistent = tmp_path / "no_such_file.csv"
        with pytest.raises(FileNotFoundError) as exc_info:
            load_raw(nonexistent)

        msg = str(exc_info.value)
        assert "no_such_file.csv" in msg or "Dataset not found" in msg

    def test_error_message_contains_placement_instructions(self, tmp_path):
        """FileNotFoundError must include actionable placement instructions."""
        from ml.data.loader import load_raw

        with pytest.raises(FileNotFoundError) as exc_info:
            load_raw(tmp_path / "missing.csv")

        msg = str(exc_info.value)
        assert "data/raw/ai4i2020.csv" in msg

    def test_default_path_documented(self):
        """DEFAULT_CSV_PATH must point to data/raw/ai4i2020.csv."""
        from ml.data.loader import DEFAULT_CSV_PATH

        assert str(DEFAULT_CSV_PATH) == str(Path("data/raw/ai4i2020.csv"))


# ---------------------------------------------------------------------------
# 3. Required-column validation
# ---------------------------------------------------------------------------


class TestColumnValidation:
    def test_missing_column_raises_value_error(self, tmp_path):
        """load_raw() raises ValueError when required columns are missing."""
        from ml.data.loader import load_raw

        bad_csv = "UDI,Product ID,Type\n1,M14860,M\n"
        csv_file = tmp_path / "bad.csv"
        csv_file.write_text(bad_csv, encoding="utf-8")

        with pytest.raises(ValueError) as exc_info:
            load_raw(csv_file)

        msg = str(exc_info.value)
        assert "missing" in msg.lower() or "required" in msg.lower()

    def test_error_lists_missing_columns(self, tmp_path):
        """ValueError must name the missing columns explicitly."""
        from ml.data.loader import load_raw

        bad_csv = "UDI,Product ID,Type\n1,M14860,M\n"
        csv_file = tmp_path / "bad.csv"
        csv_file.write_text(bad_csv, encoding="utf-8")

        with pytest.raises(ValueError) as exc_info:
            load_raw(csv_file)

        msg = str(exc_info.value)
        # At least one of the obviously missing columns should be mentioned
        assert "Air temperature" in msg or "Machine failure" in msg


# ---------------------------------------------------------------------------
# 4. Target validation
# ---------------------------------------------------------------------------


class TestTargetValidation:
    def test_target_column_is_binary(self, valid_df):
        """Machine failure column must contain only 0 and 1."""
        assert set(valid_df["Machine failure"].unique()) <= {0, 1}

    def test_target_validation_catches_non_binary(self):
        """ValidationReport must flag non-binary target values."""
        from ml.data.validation import validate

        bad_df = pd.read_csv(io.StringIO(_VALID_CSV))
        bad_df.loc[0, "Machine failure"] = 99  # invalid
        report = validate(bad_df)
        assert not report.target_ok

    def test_target_positive_rate_calculation(self):
        """Positive rate must match actual fraction of 1s in the target."""
        from ml.data.validation import validate

        df = pd.read_csv(io.StringIO(_VALID_CSV))
        report = validate(df)
        expected_rate = df["Machine failure"].mean()
        assert abs(report.target_positive_rate - expected_rate) < 1e-9


# ---------------------------------------------------------------------------
# 5. Preprocessing pipeline
# ---------------------------------------------------------------------------


class TestPreprocessing:
    def test_get_X_y_returns_correct_shapes(self, valid_df):
        """get_X_y() must return X with only feature columns and y as 1-D series."""
        from ml.data.features import get_X_y, FEATURE_COLUMNS, TARGET_COLUMN

        X, y = get_X_y(valid_df)
        assert list(X.columns) == FEATURE_COLUMNS
        assert y.name == TARGET_COLUMN
        assert len(X) == len(valid_df)
        assert len(y) == len(valid_df)

    def test_build_preprocessor_output_shape(self, valid_df):
        """fit_transform on valid data must produce (n_rows, 6) array."""
        from ml.data.features import get_X_y, build_preprocessor, FEATURE_COLUMNS

        X, _ = get_X_y(valid_df)
        preprocessor = build_preprocessor()
        X_t = preprocessor.fit_transform(X)
        assert X_t.shape == (len(valid_df), len(FEATURE_COLUMNS))

    def test_numerical_columns_are_scaled(self, valid_df):
        """StandardScaler must produce near-zero mean on numerical columns."""
        from ml.data.features import get_X_y, build_preprocessor, NUMERICAL_FEATURES
        import numpy as np

        X, _ = get_X_y(valid_df)
        preprocessor = build_preprocessor()
        X_t = preprocessor.fit_transform(X)
        # Numerical columns occupy the first len(NUMERICAL_FEATURES) positions
        num_cols = X_t[:, : len(NUMERICAL_FEATURES)]
        assert abs(num_cols.mean()) < 1e-10, "Numerical columns should have near-zero mean after scaling"

    def test_type_column_is_encoded(self, valid_df):
        """OrdinalEncoder must convert Type strings to numeric values."""
        from ml.data.features import get_X_y, build_preprocessor, NUMERICAL_FEATURES
        import numpy as np

        X, _ = get_X_y(valid_df)
        preprocessor = build_preprocessor()
        X_t = preprocessor.fit_transform(X)
        type_col = X_t[:, len(NUMERICAL_FEATURES)]  # last column = Type
        assert type_col.dtype in [float, int, "float64", "int64", np.float64, np.int64]

    def test_feature_names_out_matches_columns(self, valid_df):
        """feature_names_out() must match the order of FEATURE_COLUMNS."""
        from ml.data.features import feature_names_out, FEATURE_COLUMNS

        assert feature_names_out() == FEATURE_COLUMNS


# ---------------------------------------------------------------------------
# 6. Leakage exclusion
# ---------------------------------------------------------------------------


class TestLeakageExclusion:
    def test_failure_mode_columns_excluded_from_X(self, valid_df):
        """get_X_y() must not include any failure-mode flag columns in X."""
        from ml.data.features import get_X_y

        X, _ = get_X_y(valid_df)
        leaky_cols = {"TWF", "HDF", "PWF", "OSF", "RNF"}
        present = leaky_cols.intersection(set(X.columns))
        assert len(present) == 0, f"Leaky columns found in X: {present}"

    def test_identifier_columns_excluded_from_X(self, valid_df):
        """get_X_y() must not include UDI or Product ID in X."""
        from ml.data.features import get_X_y

        X, _ = get_X_y(valid_df)
        identifier_cols = {"UDI", "Product ID"}
        present = identifier_cols.intersection(set(X.columns))
        assert len(present) == 0, f"Identifier columns found in X: {present}"

    def test_target_column_excluded_from_X(self, valid_df):
        """get_X_y() must not include 'Machine failure' in X."""
        from ml.data.features import get_X_y

        X, _ = get_X_y(valid_df)
        assert "Machine failure" not in X.columns

    def test_excluded_columns_documented(self):
        """EXCLUDED_COLUMNS must document all leaky and identifier columns."""
        from ml.data.features import EXCLUDED_COLUMNS

        required_excluded = {"TWF", "HDF", "PWF", "OSF", "RNF", "UDI", "Product ID"}
        for col in required_excluded:
            assert col in EXCLUDED_COLUMNS, f"'{col}' missing from EXCLUDED_COLUMNS"


# ---------------------------------------------------------------------------
# 7. Reproducible train/test split
# ---------------------------------------------------------------------------


class TestSplit:
    def _make_large_df(self) -> tuple[pd.DataFrame, pd.Series]:
        """Create a dummy 100-row dataframe with 10% positive class."""
        import numpy as np

        rng = np.random.default_rng(0)
        n = 100
        df = pd.DataFrame(
            {
                "Air temperature [K]": rng.uniform(298, 302, n),
                "Process temperature [K]": rng.uniform(308, 313, n),
                "Rotational speed [rpm]": rng.integers(1200, 2000, n),
                "Torque [Nm]": rng.uniform(20, 60, n),
                "Tool wear [min]": rng.integers(0, 200, n),
                "Type": rng.choice(["L", "M", "H"], n),
            }
        )
        y = pd.Series([1 if i < 10 else 0 for i in range(n)], name="Machine failure")
        return df, y

    def test_split_is_deterministic(self):
        """Same random_state must produce identical splits."""
        from ml.data.splitting import make_split

        X, y = self._make_large_df()
        _, _, y_train_1, _ = make_split(X, y, random_state=42)
        _, _, y_train_2, _ = make_split(X, y, random_state=42)
        pd.testing.assert_series_equal(y_train_1.reset_index(drop=True), y_train_2.reset_index(drop=True))

    def test_different_seeds_produce_different_splits(self):
        """Different random states must produce different splits."""
        from ml.data.splitting import make_split

        X, y = self._make_large_df()
        _, _, y_train_42, _ = make_split(X, y, random_state=42)
        _, _, y_train_99, _ = make_split(X, y, random_state=99)
        # Very unlikely (practically impossible) that both are identical
        assert not y_train_42.reset_index(drop=True).equals(y_train_99.reset_index(drop=True))

    def test_split_sizes(self):
        """80/20 split must produce 80 train and 20 test rows for 100-row input."""
        from ml.data.splitting import make_split

        X, y = self._make_large_df()
        X_train, X_test, y_train, y_test = make_split(X, y, test_size=0.20, random_state=42)
        assert len(X_train) == 80
        assert len(X_test) == 20
        assert len(y_train) == 80
        assert len(y_test) == 20

    def test_stratification_preserves_positive_rate(self):
        """Stratified split must keep positive rates close between train and test."""
        from ml.data.splitting import make_split

        X, y = self._make_large_df()
        _, _, y_train, y_test = make_split(X, y, random_state=42)
        # Both partitions should have similar positive rates (allow ±5%)
        assert abs(y_train.mean() - y_test.mean()) < 0.05

    def test_no_overlap_between_train_and_test(self):
        """Train and test sets must not share any index values."""
        from ml.data.splitting import make_split

        X, y = self._make_large_df()
        X_train, X_test, _, _ = make_split(X, y)
        overlap = set(X_train.index).intersection(set(X_test.index))
        assert len(overlap) == 0

    def test_split_config_is_exported(self):
        """SPLIT_CONFIG must expose test_size and random_state."""
        from ml.data.splitting import SPLIT_CONFIG

        assert "test_size" in SPLIT_CONFIG
        assert "random_state" in SPLIT_CONFIG
        assert SPLIT_CONFIG["test_size"] == 0.20
        assert SPLIT_CONFIG["random_state"] == 42


# ---------------------------------------------------------------------------
# 8. Invalid input handling
# ---------------------------------------------------------------------------


class TestInvalidInput:
    def test_get_X_y_raises_on_missing_feature(self):
        """get_X_y() raises KeyError when a required feature column is absent."""
        from ml.data.features import get_X_y

        bad_df = pd.DataFrame({"Machine failure": [0, 1], "Type": ["L", "M"]})
        with pytest.raises(KeyError):
            get_X_y(bad_df)

    def test_get_X_y_raises_on_missing_target(self):
        """get_X_y() raises KeyError when the target column is absent."""
        from ml.data.features import get_X_y, FEATURE_COLUMNS
        import numpy as np

        rng = np.random.default_rng(1)
        df = pd.DataFrame(
            {
                "Air temperature [K]": rng.uniform(298, 302, 5),
                "Process temperature [K]": rng.uniform(308, 313, 5),
                "Rotational speed [rpm]": rng.integers(1200, 2000, 5),
                "Torque [Nm]": rng.uniform(20, 60, 5),
                "Tool wear [min]": rng.integers(0, 200, 5),
                "Type": ["L", "M", "H", "L", "M"],
                # No 'Machine failure' column
            }
        )
        with pytest.raises(KeyError):
            get_X_y(df)

    def test_validation_detects_duplicate_rows(self):
        """validate() must report duplicate rows when present."""
        from ml.data.validation import validate

        df = pd.read_csv(io.StringIO(_VALID_CSV))
        df = pd.concat([df, df.iloc[[0]]], ignore_index=True)  # add a duplicate
        report = validate(df)
        assert not report.duplicates_ok
        assert report.duplicate_rows >= 1

    def test_validation_detects_unexpected_type_value(self):
        """validate() must flag unexpected values in the Type column."""
        from ml.data.validation import validate

        df = pd.read_csv(io.StringIO(_VALID_CSV))
        df.loc[0, "Type"] = "Z"  # invalid type
        report = validate(df)
        assert not report.categoricals_ok
        assert "Z" in report.unexpected_type_values

    def test_validation_detects_missing_values(self):
        """validate() must flag missing values."""
        from ml.data.validation import validate
        import numpy as np

        df = pd.read_csv(io.StringIO(_VALID_CSV))
        df.loc[0, "Torque [Nm]"] = np.nan
        report = validate(df)
        assert not report.missing_values_ok
