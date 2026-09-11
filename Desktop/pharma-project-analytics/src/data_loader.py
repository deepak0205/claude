"""Data loading module for pharmaceutical inventory CSV files."""

import pandas as pd
from pathlib import Path
from typing import Optional, Tuple


def load_inventory_data(filepath: str) -> Tuple[pd.DataFrame, dict]:
    """
    Load pharmaceutical inventory data from CSV file.

    Args:
        filepath: Path to the CSV file

    Returns:
        Tuple of (DataFrame, metadata dict with load info)

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is invalid or missing required columns
    """
    file_path = Path(filepath)

    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")

    if file_path.suffix.lower() != ".csv":
        raise ValueError(f"File must be CSV format, got: {file_path.suffix}")

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {str(e)}")

    # Validate required columns
    required_columns = {
        "Batch_ID", "Medicine_Name", "Expiry_Date", "Current_Stock",
        "Reorder_Level", "Maximum_Stock", "Warehouse", "Critical_Medicine"
    }
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    metadata = {
        "filepath": str(file_path),
        "timestamp": pd.Timestamp.now().isoformat(),
        "total_records": len(df),
        "columns": list(df.columns),
    }

    return df, metadata


def get_column_types() -> dict:
    """Get the expected data types for each column."""
    return {
        "Batch_ID": str,
        "Medicine_Name": str,
        "Category": str,
        "Manufacturer": str,
        "Manufacturing_Date": str,
        "Expiry_Date": str,
        "Current_Stock": "numeric",
        "Reorder_Level": "numeric",
        "Maximum_Stock": "numeric",
        "Unit_Price": "numeric",
        "Warehouse": str,
        "Critical_Medicine": str,
    }
