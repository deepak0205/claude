"""Data quality validation module for pharmaceutical inventory data."""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Any


class ValidationResult:
    """Container for data validation results."""

    def __init__(self):
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.cleaned_df: pd.DataFrame = None
        self.is_valid: bool = True

    def add_error(self, category: str, row_index: int, column: str, message: str) -> None:
        """Add a validation error."""
        self.errors.append({
            "category": category,
            "row_index": row_index,
            "column": column,
            "message": message,
        })
        self.is_valid = False

    def add_warning(self, category: str, row_index: int, column: str, message: str) -> None:
        """Add a validation warning."""
        self.warnings.append({
            "category": category,
            "row_index": row_index,
            "column": column,
            "message": message,
        })

    def summary(self) -> Dict[str, Any]:
        """Get summary of validation results."""
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_date_format(date_str: str) -> tuple[bool, str]:
    """Validate date format (YYYY-MM-DD)."""
    if pd.isna(date_str) or date_str == "":
        return False, "Missing date"

    try:
        datetime.strptime(str(date_str), "%Y-%m-%d")
        return True, "Valid"
    except (ValueError, TypeError):
        return False, f"Invalid date format: {date_str}"


def validate_numeric_field(value: Any, field_name: str, allow_negative: bool = False) -> tuple[bool, str]:
    """Validate numeric field."""
    if pd.isna(value):
        return False, f"Missing {field_name}"

    try:
        num_value = float(value)
        if not allow_negative and num_value < 0:
            return False, f"Negative value not allowed: {num_value}"
        return True, "Valid"
    except (ValueError, TypeError):
        return False, f"Invalid numeric value: {value}"


def validate_inventory_data(df: pd.DataFrame) -> ValidationResult:
    """
    Validate pharmaceutical inventory data.

    Args:
        df: Input DataFrame

    Returns:
        ValidationResult with errors, warnings, and cleaned data
    """
    result = ValidationResult()

    if df is None or len(df) == 0:
        result.add_error("empty_data", -1, "data", "DataFrame is empty")
        return result

    df_working = df.copy()

    # Validate each row
    for idx, row in df.iterrows():
        # Validate Batch_ID
        if pd.isna(row.get("Batch_ID")) or row.get("Batch_ID") == "":
            result.add_error("missing_id", idx, "Batch_ID", "Missing Batch ID")

        # Validate Expiry_Date
        if "Expiry_Date" in row:
            is_valid, msg = validate_date_format(row["Expiry_Date"])
            if not is_valid:
                result.add_error("invalid_date", idx, "Expiry_Date", msg)

        # Validate Manufacturing_Date
        if "Manufacturing_Date" in row:
            if not pd.isna(row["Manufacturing_Date"]) and row["Manufacturing_Date"] != "":
                is_valid, msg = validate_date_format(row["Manufacturing_Date"])
                if not is_valid:
                    result.add_error("invalid_date", idx, "Manufacturing_Date", msg)

        # Validate Current_Stock
        if "Current_Stock" in row:
            is_valid, msg = validate_numeric_field(row["Current_Stock"], "Current_Stock", allow_negative=False)
            if not is_valid:
                result.add_error("invalid_stock", idx, "Current_Stock", msg)
            elif pd.notna(row["Current_Stock"]) and row["Current_Stock"] < 0:
                result.add_error("negative_stock", idx, "Current_Stock", f"Negative stock: {row['Current_Stock']}")

        # Validate Reorder_Level
        if "Reorder_Level" in row:
            is_valid, msg = validate_numeric_field(row["Reorder_Level"], "Reorder_Level", allow_negative=False)
            if not is_valid:
                result.add_error("invalid_reorder", idx, "Reorder_Level", msg)

        # Validate Maximum_Stock
        if "Maximum_Stock" in row:
            is_valid, msg = validate_numeric_field(row["Maximum_Stock"], "Maximum_Stock", allow_negative=False)
            if not is_valid:
                result.add_error("invalid_max_stock", idx, "Maximum_Stock", msg)

        # Cross-field validation (only if both values are valid numbers)
        try:
            current = row.get("Current_Stock")
            maximum = row.get("Maximum_Stock")
            if pd.notna(current) and pd.notna(maximum):
                if float(current) > float(maximum):
                    result.add_warning(
                        "overstock_warning", idx, "Current_Stock",
                        f"Current stock ({current}) exceeds max ({maximum})"
                    )
        except (TypeError, ValueError):
            pass

        # Validate Critical_Medicine field
        if "Critical_Medicine" in row and pd.notna(row["Critical_Medicine"]):
            if str(row["Critical_Medicine"]).lower() not in ["yes", "no", "true", "false"]:
                result.add_error("invalid_critical", idx, "Critical_Medicine", f"Invalid value: {row['Critical_Medicine']}")

    # Check for duplicates (same Batch_ID)
    if "Batch_ID" in df.columns:
        duplicates = df[df.duplicated(subset=["Batch_ID"], keep=False)]
        for idx, row in duplicates.iterrows():
            result.add_warning("duplicate_batch_id", idx, "Batch_ID", f"Duplicate Batch ID: {row['Batch_ID']}")

    result.cleaned_df = df_working

    return result


def get_data_quality_report(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate a data quality report for the dataset."""
    validation = validate_inventory_data(df)

    return {
        "valid": validation.is_valid,
        "total_records": len(df),
        "error_count": len(validation.errors),
        "warning_count": len(validation.warnings),
        "missing_values": df.isnull().sum().to_dict(),
        "validation_summary": validation.summary(),
    }
