"""ml/data/splitting.py — Reproducible train/test split for the AI4I 2020 dataset.

DESIGN DECISIONS
----------------
- Stratified split on the target column (Machine failure) to preserve the
  ~3.4% positive-class ratio in both train and test sets.
- Fixed random_state (RANDOM_STATE = 42) for reproducibility across all phases.
- 80/20 split (TEST_SIZE = 0.20) — a standard choice for a 10,000-row dataset
  that gives 2,000 test rows (≈68 positive examples at 3.4% rate) — enough
  to evaluate precision/recall reliably.
- Split metadata is exposed as a module-level constant dict (SPLIT_CONFIG) so
  that Phase 3 can import and document the exact same configuration.

SPLIT CONFIGURATION
-------------------
  RANDOM_STATE : 42
  TEST_SIZE    : 0.20  (2,000 rows)
  TRAIN_SIZE   : 0.80  (8,000 rows)
  STRATEGY     : stratified on 'Machine failure'
"""

from __future__ import annotations

import pandas as pd
from sklearn.model_selection import train_test_split

# ---------------------------------------------------------------------------
# Split configuration — import this dict in Phase 3 to guarantee consistency
# ---------------------------------------------------------------------------

SPLIT_CONFIG: dict = {
    "test_size": 0.20,
    "random_state": 42,
    "stratify_column": "Machine failure",
    "description": (
        "80/20 stratified split on 'Machine failure'. "
        "Stratification preserves the class imbalance ratio in both partitions."
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def make_split(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = SPLIT_CONFIG["test_size"],
    random_state: int = SPLIT_CONFIG["random_state"],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Create a reproducible stratified train/test split.

    Parameters
    ----------
    X:
        Feature matrix (as returned by :func:`ml.data.features.get_X_y`).
    y:
        Target series (Machine failure).
    test_size:
        Fraction of data to reserve for testing.  Default 0.20.
    random_state:
        Seed for reproducibility.  Default 42.

    Returns
    -------
    X_train, X_test, y_train, y_test
        Four DataFrames/Series with consistent index alignment.
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )
    return X_train, X_test, y_train, y_test


def split_summary(y_train: pd.Series, y_test: pd.Series) -> str:
    """Return a short human-readable summary of the split."""
    n_train, n_test = len(y_train), len(y_test)
    pos_train = int(y_train.sum())
    pos_test = int(y_test.sum())
    lines = [
        "Train/Test Split Summary",
        f"  Train : {n_train} rows  ({pos_train} failures, "
        f"{pos_train / n_train:.2%} positive rate)",
        f"  Test  : {n_test} rows  ({pos_test} failures, "
        f"{pos_test / n_test:.2%} positive rate)",
        f"  Config: test_size={SPLIT_CONFIG['test_size']}, "
        f"random_state={SPLIT_CONFIG['random_state']}, stratified=True",
    ]
    return "\n".join(lines)
