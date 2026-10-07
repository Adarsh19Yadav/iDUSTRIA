"""ml/data/validation.py — Dataset quality checks for the AI4I 2020 dataset.

Produces a structured ValidationReport that can be inspected programmatically
or printed as a human-readable summary.  No data is modified here.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pandas as pd

from ml.data.loader import REQUIRED_COLUMNS

# ---------------------------------------------------------------------------
# Expected schema properties
# ---------------------------------------------------------------------------

EXPECTED_ROWS = 10_000
EXPECTED_COLS = 14

#: Columns that must be integer binary flags (0/1).
BINARY_INT_COLUMNS = ["Machine failure", "TWF", "HDF", "PWF", "OSF", "RNF"]

#: Allowed values for the 'Type' categorical column.
TYPE_ALLOWED_VALUES = {"L", "M", "H"}

#: Plausible numerical ranges (inclusive) derived from dataset documentation.
NUMERICAL_RANGES: dict[str, tuple[float, float]] = {
    "Air temperature [K]": (295.0, 305.0),
    "Process temperature [K]": (305.0, 315.0),
    "Rotational speed [rpm]": (1000, 3000),
    "Torque [Nm]": (0.0, 80.0),
    "Tool wear [min]": (0, 300),
}


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class ValidationReport:
    """Results of a full dataset quality check."""

    # Basic shape
    actual_rows: int = 0
    actual_cols: int = 0
    shape_ok: bool = False

    # Columns
    found_columns: list[str] = dataclasses.field(default_factory=list)
    missing_columns: list[str] = dataclasses.field(default_factory=list)
    columns_ok: bool = False

    # Dtypes
    dtype_issues: list[str] = dataclasses.field(default_factory=list)
    dtypes_ok: bool = False

    # Missing values
    missing_value_counts: dict[str, int] = dataclasses.field(default_factory=dict)
    missing_values_ok: bool = False

    # Duplicates
    duplicate_rows: int = 0
    duplicates_ok: bool = False

    # Categorical values
    type_unique_values: set[str] = dataclasses.field(default_factory=set)
    unexpected_type_values: set[str] = dataclasses.field(default_factory=set)
    categoricals_ok: bool = False

    # Numerical ranges
    out_of_range: dict[str, dict[str, Any]] = dataclasses.field(default_factory=dict)
    ranges_ok: bool = False

    # Target distribution
    target_value_counts: dict[int, int] = dataclasses.field(default_factory=dict)
    target_positive_rate: float = 0.0
    target_ok: bool = False

    # Invalid binary flag values
    binary_flag_issues: list[str] = dataclasses.field(default_factory=list)
    binary_flags_ok: bool = False

    @property
    def all_ok(self) -> bool:
        return all(
            [
                self.shape_ok,
                self.columns_ok,
                self.dtypes_ok,
                self.missing_values_ok,
                self.duplicates_ok,
                self.categoricals_ok,
                self.ranges_ok,
                self.target_ok,
                self.binary_flags_ok,
            ]
        )

    def summary(self) -> str:
        """Return a human-readable summary of the validation results."""
        lines: list[str] = [
            "=" * 60,
            "AI4I 2020 Dataset Validation Report",
            "=" * 60,
            "",
            f"[{'OK' if self.shape_ok else 'FAIL'}] Shape: {self.actual_rows} rows × {self.actual_cols} cols"
            f"  (expected {EXPECTED_ROWS} × {EXPECTED_COLS})",
            "",
            f"[{'OK' if self.columns_ok else 'FAIL'}] Columns",
        ]
        if self.missing_columns:
            lines.append(f"      Missing: {self.missing_columns}")
        lines += [
            "",
            f"[{'OK' if self.dtypes_ok else 'WARN'}] Data types",
        ]
        if self.dtype_issues:
            for issue in self.dtype_issues:
                lines.append(f"      {issue}")
        lines += [
            "",
            f"[{'OK' if self.missing_values_ok else 'FAIL'}] Missing values",
        ]
        non_zero = {k: v for k, v in self.missing_value_counts.items() if v > 0}
        if non_zero:
            for col, cnt in non_zero.items():
                lines.append(f"      {col}: {cnt} missing")
        else:
            lines.append("      None")
        lines += [
            "",
            f"[{'OK' if self.duplicates_ok else 'FAIL'}] Duplicate rows: {self.duplicate_rows}",
            "",
            f"[{'OK' if self.categoricals_ok else 'FAIL'}] Type categories: {sorted(self.type_unique_values)}",
        ]
        if self.unexpected_type_values:
            lines.append(f"      Unexpected values: {self.unexpected_type_values}")
        lines += [
            "",
            f"[{'OK' if self.ranges_ok else 'FAIL'}] Numerical ranges",
        ]
        if self.out_of_range:
            for col, info in self.out_of_range.items():
                lines.append(
                    f"      {col}: {info['count']} values outside "
                    f"[{info['expected_min']}, {info['expected_max']}]  "
                    f"(actual min={info['actual_min']:.2f}, max={info['actual_max']:.2f})"
                )
        else:
            lines.append("      All within expected ranges")
        lines += [
            "",
            f"[{'OK' if self.target_ok else 'FAIL'}] Target 'Machine failure'",
            f"      0 (no failure): {self.target_value_counts.get(0, 0)}",
            f"      1 (failure)   : {self.target_value_counts.get(1, 0)}",
            f"      Positive rate : {self.target_positive_rate:.2%}",
            "",
            f"[{'OK' if self.binary_flags_ok else 'FAIL'}] Binary failure-mode flags",
        ]
        if self.binary_flag_issues:
            for issue in self.binary_flag_issues:
                lines.append(f"      {issue}")
        else:
            lines.append("      All flags are valid binary (0/1)")
        lines += [
            "",
            "─" * 60,
            f"Overall: {'PASS' if self.all_ok else 'ISSUES FOUND'}",
            "=" * 60,
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------


def validate(df: pd.DataFrame) -> ValidationReport:
    """Run all quality checks on *df* and return a ``ValidationReport``.

    Parameters
    ----------
    df:
        The raw DataFrame as returned by :func:`ml.data.loader.load_raw`.

    Returns
    -------
    ValidationReport
        All check results collected into one object.
    """
    report = ValidationReport()

    # 1. Shape ----------------------------------------------------------------
    report.actual_rows, report.actual_cols = df.shape
    report.shape_ok = (
        report.actual_rows == EXPECTED_ROWS and report.actual_cols == EXPECTED_COLS
    )

    # 2. Columns --------------------------------------------------------------
    report.found_columns = list(df.columns)
    report.missing_columns = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    report.columns_ok = len(report.missing_columns) == 0

    # 3. Data types -----------------------------------------------------------
    dtype_issues: list[str] = []
    for col in BINARY_INT_COLUMNS:
        if col in df.columns and not pd.api.types.is_integer_dtype(df[col]):
            dtype_issues.append(f"{col!r} expected integer, got {df[col].dtype}")
    for col in ["Air temperature [K]", "Process temperature [K]", "Torque [Nm]"]:
        if col in df.columns and not pd.api.types.is_float_dtype(df[col]):
            dtype_issues.append(f"{col!r} expected float, got {df[col].dtype}")
    report.dtype_issues = dtype_issues
    report.dtypes_ok = len(dtype_issues) == 0

    # 4. Missing values -------------------------------------------------------
    report.missing_value_counts = df.isnull().sum().to_dict()
    report.missing_values_ok = df.isnull().sum().sum() == 0

    # 5. Duplicates -----------------------------------------------------------
    report.duplicate_rows = int(df.duplicated().sum())
    report.duplicates_ok = report.duplicate_rows == 0

    # 6. Categorical values ---------------------------------------------------
    if "Type" in df.columns:
        report.type_unique_values = set(df["Type"].unique())
        report.unexpected_type_values = report.type_unique_values - TYPE_ALLOWED_VALUES
        report.categoricals_ok = len(report.unexpected_type_values) == 0
    else:
        report.categoricals_ok = False

    # 7. Numerical ranges -----------------------------------------------------
    out_of_range: dict[str, dict[str, Any]] = {}
    for col, (lo, hi) in NUMERICAL_RANGES.items():
        if col not in df.columns:
            continue
        mask = (df[col] < lo) | (df[col] > hi)
        count = int(mask.sum())
        if count > 0:
            out_of_range[col] = {
                "count": count,
                "expected_min": lo,
                "expected_max": hi,
                "actual_min": float(df[col].min()),
                "actual_max": float(df[col].max()),
            }
    report.out_of_range = out_of_range
    report.ranges_ok = len(out_of_range) == 0

    # 8. Target distribution --------------------------------------------------
    if "Machine failure" in df.columns:
        vc = df["Machine failure"].value_counts().to_dict()
        report.target_value_counts = {int(k): int(v) for k, v in vc.items()}
        total = df.shape[0]
        report.target_positive_rate = report.target_value_counts.get(1, 0) / total
        report.target_ok = set(df["Machine failure"].unique()) <= {0, 1}

    # 9. Binary flag validity -------------------------------------------------
    binary_flag_issues: list[str] = []
    for col in BINARY_INT_COLUMNS:
        if col not in df.columns:
            continue
        bad = df[~df[col].isin([0, 1])]
        if len(bad) > 0:
            binary_flag_issues.append(
                f"{col!r}: {len(bad)} rows contain values outside {{0, 1}}"
            )
    report.binary_flag_issues = binary_flag_issues
    report.binary_flags_ok = len(binary_flag_issues) == 0

    return report
