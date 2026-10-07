"""ml/data/features.py — Feature preparation for the AI4I 2020 dataset.

LEAKAGE ANALYSIS
----------------
The dataset contains failure-mode sub-columns that are derived from the same
event that produces the target label (Machine failure = 1).  These columns
are EXCLUDED from the feature set to prevent target leakage:

  Column  | Reason for exclusion
  --------|--------------------------------------------------------
  TWF     | Tool Wear Failure — a failure sub-type of the target
  HDF     | Heat Dissipation Failure — a failure sub-type of the target
  PWF     | Power Failure — a failure sub-type of the target
  OSF     | Overstrain Failure — a failure sub-type of the target
  RNF     | Random Failures — a failure sub-type of the target

  Column  | Reason for exclusion
  --------|--------------------------------------------------------
  UDI     | Sequential integer row identifier — no predictive signal
  Product ID | Alphanumeric product serial — encodes UDI + Type, no
           | additional signal; would create high-cardinality noise

FEATURE GROUPS
--------------
Numerical (continuous / sensor readings):
  - Air temperature [K]
  - Process temperature [K]
  - Rotational speed [rpm]
  - Torque [Nm]
  - Tool wear [min]

Categorical:
  - Type  (product quality variant: L / M / H)

TARGET
------
  - Machine failure  (binary: 0 = no failure, 1 = failure)

DESIGN DECISIONS
----------------
- StandardScaler is used for numerical features (zero mean, unit variance)
  because the downstream models (SVM, logistic regression, etc.) are
  scale-sensitive.  Tree-based models are unaffected but not harmed by this.
- OrdinalEncoder is used for 'Type' rather than one-hot encoding to keep the
  feature matrix compact.  One-hot can be substituted trivially later.
- The preprocessor is returned as a fitted or unfitted sklearn Pipeline so
  that Phase 3 can call `pipe.fit_transform(X_train)` and `pipe.transform(X_test)`
  without any test-set information leaking into the training process.
"""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder, StandardScaler

# ---------------------------------------------------------------------------
# Column lists
# ---------------------------------------------------------------------------

TARGET_COLUMN = "Machine failure"

#: Columns excluded from modelling and the reasons.
EXCLUDED_COLUMNS: dict[str, str] = {
    "UDI": "Sequential row identifier — no predictive signal",
    "Product ID": "Alphanumeric serial encoding UDI + Type — no additional signal",
    "TWF": "Tool Wear Failure sub-type — derived from the target (leakage)",
    "HDF": "Heat Dissipation Failure sub-type — derived from the target (leakage)",
    "PWF": "Power Failure sub-type — derived from the target (leakage)",
    "OSF": "Overstrain Failure sub-type — derived from the target (leakage)",
    "RNF": "Random Failure sub-type — derived from the target (leakage)",
}

NUMERICAL_FEATURES: list[str] = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]

CATEGORICAL_FEATURES: list[str] = ["Type"]

#: Ordered list of all feature columns (numerical first, then categorical).
FEATURE_COLUMNS: list[str] = NUMERICAL_FEATURES + CATEGORICAL_FEATURES


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_X_y(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Split the raw dataframe into feature matrix X and target series y.

    Excluded columns (leaky failure-mode flags and identifiers) are dropped
    here so that the returned ``X`` contains only ``FEATURE_COLUMNS``.

    Parameters
    ----------
    df:
        Raw dataset as returned by :func:`ml.data.loader.load_raw`.

    Returns
    -------
    X : pd.DataFrame
        Feature columns only (no target, no excluded columns).
    y : pd.Series
        Binary target (Machine failure).

    Raises
    ------
    KeyError
        If any expected feature or target column is absent.
    """
    missing_features = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing_features:
        raise KeyError(f"Missing feature columns: {missing_features}")
    if TARGET_COLUMN not in df.columns:
        raise KeyError(f"Target column '{TARGET_COLUMN}' not found in dataframe.")

    X = df[FEATURE_COLUMNS].copy()
    y = df[TARGET_COLUMN].copy()
    return X, y


def build_preprocessor() -> ColumnTransformer:
    """Return an *unfitted* sklearn ColumnTransformer for the feature set.

    Apply ``preprocessor.fit_transform(X_train)`` and
    ``preprocessor.transform(X_test)`` in Phase 3.

    Returns
    -------
    ColumnTransformer
        Unfitted transformer: StandardScaler for numerical columns,
        OrdinalEncoder for categorical columns.
    """
    numerical_pipe = Pipeline(
        [("scaler", StandardScaler())],
    )
    categorical_pipe = Pipeline(
        [
            (
                "ordinal",
                OrdinalEncoder(
                    categories=[["L", "M", "H"]],  # ordered L < M < H
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,
                ),
            )
        ],
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numerical_pipe, NUMERICAL_FEATURES),
            ("cat", categorical_pipe, CATEGORICAL_FEATURES),
        ],
        remainder="drop",  # silently drops any column not in either list
    )
    return preprocessor


def feature_names_out() -> list[str]:
    """Return the ordered output column names after preprocessing.

    The ColumnTransformer preserves the column order: numerical first,
    then categorical.
    """
    return NUMERICAL_FEATURES + CATEGORICAL_FEATURES
