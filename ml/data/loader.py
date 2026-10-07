"""ml/data/loader.py — Raw data ingestion for the AI4I 2020 dataset.

SYNTHETIC DATA NOTICE
---------------------
The AI4I 2020 Predictive Maintenance Dataset is a *synthetic* dataset created
for research purposes. It does NOT represent real factory telemetry. Do not
present statistics derived from this dataset as measurements from real
industrial equipment.

Dataset source : https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset
Authors        : S. Matzka
Licence        : CC BY 4.0
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Expected schema
# ---------------------------------------------------------------------------

#: All columns that must be present in the raw CSV.
REQUIRED_COLUMNS: list[str] = [
    "UDI",
    "Product ID",
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
    "Machine failure",
    "TWF",
    "HDF",
    "PWF",
    "OSF",
    "RNF",
]

#: Default path to the raw CSV file (relative to project root).
DEFAULT_CSV_PATH = Path("data/raw/ai4i2020.csv")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_raw(path: str | Path | None = None) -> pd.DataFrame:
    """Load the raw AI4I 2020 CSV and return it unchanged.

    Parameters
    ----------
    path:
        Path to the CSV file.  Defaults to ``data/raw/ai4i2020.csv``
        (relative to the working directory, which should be the project root).

    Returns
    -------
    pd.DataFrame
        The raw dataset with all original columns and dtypes.

    Raises
    ------
    FileNotFoundError
        If the CSV file does not exist.
    ValueError
        If one or more required columns are missing from the CSV.
    """
    csv_path = Path(path) if path is not None else DEFAULT_CSV_PATH

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at '{csv_path}'.\n\n"
            "To obtain the AI4I 2020 Predictive Maintenance Dataset:\n"
            "  1. Visit https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset\n"
            "  2. Download 'ai4i2020.csv'.\n"
            "  3. Place it at: data/raw/ai4i2020.csv\n\n"
            "The dataset is synthetic (not real factory data) and is released under CC BY 4.0.\n"
            "Do NOT commit large CSV files to the repository."
        )

    df = pd.read_csv(csv_path)
    _validate_columns(df)
    return df


def _validate_columns(df: pd.DataFrame) -> None:
    """Raise ValueError if any required column is absent."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"The dataset is missing {len(missing)} required column(s): {missing}.\n"
            "Check that the correct file is placed at data/raw/ai4i2020.csv.\n"
            f"Expected columns: {REQUIRED_COLUMNS}"
        )
