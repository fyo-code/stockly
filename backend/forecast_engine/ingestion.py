from datetime import datetime, timezone
from typing import TypedDict
import pandas as pd


class SalesRow(TypedDict):
    sku_id: str
    store_id: str
    sale_date: str  # YYYY-MM-DD
    units_sold: int
    units_returned: int | None


def load_sales_data(csv_path: str) -> pd.DataFrame:
    """Load and validate sales CSV.

    Loads a CSV file containing sales data with columns:
    sku_id, store_id, sale_date, units_sold, units_returned.
    Validates data integrity and normalizes dates to UTC timezone.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        Cleaned pandas DataFrame with validated and normalized columns.

    Raises:
        FileNotFoundError: If CSV file does not exist.
        ValueError: If required columns are missing or data validation fails.
    """
    required_columns = {"sku_id", "store_id", "sale_date", "units_sold", "units_returned"}

    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {e}")

    # Check for required columns
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Validate data types and content
    if not validate_sales_data(df):
        raise ValueError("Data validation failed. See logs for details.")

    # Normalize dates to UTC
    df["sale_date"] = pd.to_datetime(df["sale_date"], format="%Y-%m-%d", errors="coerce")
    df["sale_date"] = df["sale_date"].dt.tz_localize("UTC")

    # Ensure numeric columns are numeric
    df["units_sold"] = pd.to_numeric(df["units_sold"], errors="coerce")
    df["units_returned"] = pd.to_numeric(df["units_returned"], errors="coerce")

    # Convert to correct types
    df["sku_id"] = df["sku_id"].astype(str)
    df["store_id"] = df["store_id"].astype(str)

    # Remove rows with NaN in critical columns after conversion
    df = df.dropna(subset=["sale_date", "units_sold"])

    return df


def validate_sales_data(df: pd.DataFrame) -> bool:
    """Check data integrity of sales DataFrame.

    Validates:
    - All required columns are present
    - sale_date can be parsed as ISO format (YYYY-MM-DD)
    - units_sold and units_returned are numeric or convertible
    - units_sold is non-negative
    - units_returned is non-negative (where present)

    Args:
        df: DataFrame to validate.

    Returns:
        True if all validations pass, False otherwise.
    """
    required_columns = {"sku_id", "store_id", "sale_date", "units_sold", "units_returned"}

    # Check columns exist
    if not required_columns.issubset(df.columns):
        missing = required_columns - set(df.columns)
        print(f"Missing columns: {missing}")
        return False

    # Check that dataframe is not empty
    if df.empty:
        print("DataFrame is empty")
        return False

    # Validate sale_date format
    try:
        pd.to_datetime(df["sale_date"], format="%Y-%m-%d")
    except Exception as e:
        print(f"Invalid sale_date format (expected YYYY-MM-DD): {e}")
        return False

    # Validate units_sold is numeric
    try:
        units_sold = pd.to_numeric(df["units_sold"], errors="coerce")
        if units_sold.isna().any():
            print("Some units_sold values could not be converted to numeric")
            return False
    except Exception as e:
        print(f"units_sold validation error: {e}")
        return False

    # Validate units_sold is non-negative
    if (units_sold < 0).any():
        print("Found negative units_sold values")
        return False

    # Validate units_returned is numeric (where present)
    try:
        units_returned = pd.to_numeric(df["units_returned"], errors="coerce")
        # Check non-null values are non-negative
        non_null_returns = units_returned.dropna()
        if (non_null_returns < 0).any():
            print("Found negative units_returned values")
            return False
    except Exception as e:
        print(f"units_returned validation error: {e}")
        return False

    # Validate sku_id and store_id are not empty
    if df["sku_id"].isna().any() or df["sku_id"].astype(str).str.strip().eq("").any():
        print("Found empty or null sku_id values")
        return False

    if df["store_id"].isna().any() or df["store_id"].astype(str).str.strip().eq("").any():
        print("Found empty or null store_id values")
        return False

    return True
