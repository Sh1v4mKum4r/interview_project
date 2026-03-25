"""
File ingestion module for CSV/Excel data upload, parsing, and validation.
Converts uploaded financial data into the internal data format used by all engine modules.
"""

import io
import pandas as pd
import numpy as np
from typing import Optional


def ingest_file(file_content: bytes, filename: str) -> dict:
    """
    Parse an uploaded CSV or Excel file into the internal data format.

    Expects a file with:
    - A date column (auto-detected)
    - Numeric columns for each asset (prices or returns)

    Returns the internal data format dict with returns, prices, and metadata.
    Raises ValueError with descriptive messages for invalid formats.
    """
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "csv":
        df = _parse_csv(file_content)
    elif ext in ("xlsx", "xls"):
        df = _parse_excel(file_content)
    else:
        raise ValueError(
            f"Unsupported file format: .{ext}. Please upload a .csv or .xlsx file."
        )

    df = _validate_and_clean(df)
    date_col = _detect_date_column(df)
    df = _set_date_index(df, date_col)
    asset_columns = [c for c in df.columns if c != date_col]

    if len(asset_columns) == 0:
        raise ValueError("No numeric asset columns found in the uploaded file.")

    prices_df = df[asset_columns].copy()
    is_returns = _detect_if_returns(prices_df)

    if is_returns:
        returns_df = prices_df.copy()
        prices_df = _returns_to_prices(returns_df, base_price=100.0)
    else:
        returns_df = np.log(prices_df / prices_df.shift(1)).dropna()
        prices_df = prices_df.loc[returns_df.index]

    metadata = _infer_metadata(asset_columns)

    return {
        "returns": returns_df,
        "prices": prices_df,
        "metadata": metadata,
    }


def _parse_csv(content: bytes) -> pd.DataFrame:
    """Parse CSV content into a DataFrame."""
    try:
        return pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"Failed to parse CSV file: {e}")


def _parse_excel(content: bytes) -> pd.DataFrame:
    """Parse Excel content into a DataFrame."""
    try:
        return pd.read_excel(io.BytesIO(content), engine="openpyxl")
    except Exception as e:
        raise ValueError(f"Failed to parse Excel file: {e}")


def _validate_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Validate basic structure and clean the DataFrame."""
    if df.empty:
        raise ValueError("The uploaded file is empty.")

    if len(df.columns) < 2:
        raise ValueError(
            "The file must have at least a date column and one asset column."
        )

    # Drop fully empty rows and columns
    df = df.dropna(how="all").dropna(axis=1, how="all")

    if len(df) < 10:
        raise ValueError(
            f"The file has only {len(df)} rows. At least 10 data points are required."
        )

    return df


def _detect_date_column(df: pd.DataFrame) -> str:
    """Auto-detect which column contains dates."""
    # Check column names for date-like names
    date_names = {"date", "dates", "timestamp", "time", "datetime", "day", "period"}
    for col in df.columns:
        if str(col).lower().strip() in date_names:
            return col

    # Try parsing each column as dates
    for col in df.columns:
        if df[col].dtype == "object" or df[col].dtype.name.startswith("datetime"):
            try:
                pd.to_datetime(df[col].head(5))
                return col
            except (ValueError, TypeError):
                continue

    # Default to first column
    try:
        pd.to_datetime(df.iloc[:, 0].head(5))
        return df.columns[0]
    except (ValueError, TypeError):
        raise ValueError(
            "Could not detect a date column. Please ensure your file has a column "
            "named 'Date' or 'Timestamp' with parseable date values."
        )


def _set_date_index(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """Set the date column as the index and sort chronologically."""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()

    # Convert remaining columns to numeric
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop columns that are entirely NaN after numeric conversion
    df = df.dropna(axis=1, how="all")

    # Forward-fill then back-fill small gaps (up to 5 days)
    df = df.ffill(limit=5).bfill(limit=5)

    remaining_nans = df.isna().sum().sum()
    if remaining_nans > 0:
        nan_cols = df.columns[df.isna().any()].tolist()
        raise ValueError(
            f"Columns {nan_cols} have too many missing values to fill. "
            "Please clean your data and re-upload."
        )

    return df


def _detect_if_returns(df: pd.DataFrame) -> bool:
    """
    Heuristic: if most values are between -0.5 and 0.5 and the mean is near zero,
    the data is likely returns. If values are > 1, it's likely prices.
    """
    sample = df.iloc[:min(50, len(df))]
    abs_mean = sample.abs().mean().mean()
    max_val = sample.abs().max().max()

    if abs_mean < 0.1 and max_val < 1.0:
        return True
    return False


def _returns_to_prices(returns_df: pd.DataFrame, base_price: float = 100.0) -> pd.DataFrame:
    """Convert log-returns to price series starting at base_price."""
    cumulative = returns_df.cumsum()
    prices = base_price * np.exp(cumulative)
    return prices


def _infer_metadata(columns: list) -> dict:
    """
    Infer asset metadata from column names.
    For uploaded data, we use simple heuristics. Users can always use synthetic data
    for full metadata coverage.
    """
    known_equities = {
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA",
        "JPM", "GS", "BAC", "MS", "C", "WFC",
        "JNJ", "PFE", "UNH", "MRK", "ABT",
        "XOM", "CVX", "COP", "SLB", "EOG",
    }
    known_bonds = {"GOV", "CORP", "UST", "BOND", "TBILL", "TNOTE"}
    known_commodities = {"GOLD", "OIL", "NATGAS", "SILVER", "COPPER", "WHEAT", "CORN"}
    known_fx = {"EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"}

    asset_classes = {}
    sectors = {}
    ratings = {}

    for col in columns:
        upper = col.upper().replace(" ", "").replace("_", "")
        if upper in known_equities or col.upper() in known_equities:
            asset_classes[col] = "equity"
            sectors[col] = "unknown"
        elif any(b in upper for b in known_bonds):
            asset_classes[col] = "fixed_income"
            ratings[col] = "A"
        elif upper in known_commodities or any(c in upper for c in known_commodities):
            asset_classes[col] = "commodity"
        elif upper in known_fx or any(f in upper for f in known_fx):
            asset_classes[col] = "fx"
        elif "CALL" in upper or "PUT" in upper or "OPT" in upper:
            asset_classes[col] = "derivative"
        else:
            asset_classes[col] = "equity"  # default assumption
            sectors[col] = "unknown"

    return {
        "asset_classes": asset_classes,
        "sectors": sectors,
        "ratings": ratings,
        "derivatives": {},
    }
