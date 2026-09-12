"""Unit tests for data quality validation module."""

import pytest
import pandas as pd
from datetime import datetime, date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_quality import (
    ValidationResult, validate_date_format, validate_numeric_field,
    validate_inventory_data, get_data_quality_report
)


class TestValidateDateFormat:
    """Test date format validation."""

    def test_valid_date(self):
        is_valid, msg = validate_date_format("2026-09-15")
        assert is_valid is True
        assert msg == "Valid"

    def test_invalid_format(self):
        is_valid, msg = validate_date_format("15/09/2026")
        assert is_valid is False
        assert "Invalid date format" in msg

    def test_invalid_date_values(self):
        is_valid, msg = validate_date_format("2026-13-45")
        assert is_valid is False

    def test_missing_date(self):
        is_valid, msg = validate_date_format("")
        assert is_valid is False
        assert "Missing" in msg

    def test_none_date(self):
        is_valid, msg = validate_date_format(None)
        assert is_valid is False


class TestValidateNumericField:
    """Test numeric field validation."""

    def test_valid_positive(self):
        is_valid, msg = validate_numeric_field(100, "stock")
        assert is_valid is True

    def test_valid_zero(self):
        is_valid, msg = validate_numeric_field(0, "stock")
        assert is_valid is True

    def test_negative_not_allowed(self):
        is_valid, msg = validate_numeric_field(-50, "stock", allow_negative=False)
        assert is_valid is False
        assert "Negative" in msg

    def test_negative_allowed(self):
        is_valid, msg = validate_numeric_field(-50, "price", allow_negative=True)
        assert is_valid is True

    def test_missing_value(self):
        is_valid, msg = validate_numeric_field(None, "stock")
        assert is_valid is False
        assert "Missing" in msg

    def test_invalid_numeric(self):
        is_valid, msg = validate_numeric_field("abc", "stock")
        assert is_valid is False


class TestValidateInventoryData:
    """Test inventory data validation."""

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = validate_inventory_data(df)
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_missing_batch_id(self):
        df = pd.DataFrame({
            "Batch_ID": [None, "BATCH-002"],
            "Expiry_Date": ["2026-12-31", "2026-12-31"],
            "Current_Stock": [100, 200],
            "Reorder_Level": [50, 50],
            "Maximum_Stock": [500, 500],
            "Warehouse": ["WH-1", "WH-1"],
            "Critical_Medicine": ["No", "No"],
        })
        result = validate_inventory_data(df)
        assert len(result.errors) > 0
        assert any("Batch_ID" in e["column"] for e in result.errors)

    def test_invalid_expiry_date(self):
        df = pd.DataFrame({
            "Batch_ID": ["BATCH-001"],
            "Expiry_Date": ["2026-13-45"],
            "Current_Stock": [100],
            "Reorder_Level": [50],
            "Maximum_Stock": [500],
            "Warehouse": ["WH-1"],
            "Critical_Medicine": ["No"],
        })
        result = validate_inventory_data(df)
        assert len(result.errors) > 0

    def test_negative_stock(self):
        df = pd.DataFrame({
            "Batch_ID": ["BATCH-001"],
            "Expiry_Date": ["2026-12-31"],
            "Current_Stock": [-50],
            "Reorder_Level": [50],
            "Maximum_Stock": [500],
            "Warehouse": ["WH-1"],
            "Critical_Medicine": ["No"],
        })
        result = validate_inventory_data(df)
        assert len(result.errors) > 0

    def test_valid_data(self):
        df = pd.DataFrame({
            "Batch_ID": ["BATCH-001"],
            "Expiry_Date": ["2026-12-31"],
            "Current_Stock": [100],
            "Reorder_Level": [50],
            "Maximum_Stock": [500],
            "Warehouse": ["WH-1"],
            "Critical_Medicine": ["No"],
        })
        result = validate_inventory_data(df)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_duplicate_batch_id_warning(self):
        df = pd.DataFrame({
            "Batch_ID": ["BATCH-001", "BATCH-001"],
            "Expiry_Date": ["2026-12-31", "2026-12-31"],
            "Current_Stock": [100, 100],
            "Reorder_Level": [50, 50],
            "Maximum_Stock": [500, 500],
            "Warehouse": ["WH-1", "WH-1"],
            "Critical_Medicine": ["No", "No"],
        })
        result = validate_inventory_data(df)
        assert len(result.warnings) > 0

    def test_overstock_warning(self):
        df = pd.DataFrame({
            "Batch_ID": ["BATCH-001"],
            "Expiry_Date": ["2026-12-31"],
            "Current_Stock": [1000],
            "Reorder_Level": [50],
            "Maximum_Stock": [500],
            "Warehouse": ["WH-1"],
            "Critical_Medicine": ["No"],
        })
        result = validate_inventory_data(df)
        assert len(result.warnings) > 0

    def test_missing_expiry_date_error(self):
        df = pd.DataFrame({
            "Batch_ID": ["BATCH-001"],
            "Expiry_Date": [None],
            "Current_Stock": [100],
            "Reorder_Level": [50],
            "Maximum_Stock": [500],
            "Warehouse": ["WH-1"],
            "Critical_Medicine": ["No"],
        })
        result = validate_inventory_data(df)
        assert any(e["column"] == "Expiry_Date" for e in result.errors)


class TestDataQualityReport:
    """Test data quality report generation."""

    def test_report_structure(self):
        df = pd.DataFrame({
            "Batch_ID": ["BATCH-001"],
            "Expiry_Date": ["2026-12-31"],
            "Current_Stock": [100],
            "Reorder_Level": [50],
            "Maximum_Stock": [500],
            "Warehouse": ["WH-1"],
            "Critical_Medicine": ["No"],
        })
        report = get_data_quality_report(df)
        assert "valid" in report
        assert "total_records" in report
        assert "error_count" in report
        assert "warning_count" in report

    def test_report_with_errors(self):
        df = pd.DataFrame({
            "Batch_ID": [None, "BATCH-002"],
            "Expiry_Date": ["2026-13-45", "2026-12-31"],
            "Current_Stock": [100, 200],
            "Reorder_Level": [50, 50],
            "Maximum_Stock": [500, 500],
            "Warehouse": ["WH-1", "WH-1"],
            "Critical_Medicine": ["No", "No"],
        })
        report = get_data_quality_report(df)
        assert report["valid"] is False
        assert report["error_count"] > 0


class TestValidationResult:
    """Test ValidationResult class."""

    def test_add_error(self):
        result = ValidationResult()
        result.add_error("test", 0, "field", "Test error")
        assert len(result.errors) == 1
        assert result.is_valid is False

    def test_add_warning(self):
        result = ValidationResult()
        result.add_warning("test", 0, "field", "Test warning")
        assert len(result.warnings) == 1
        assert result.is_valid is True

    def test_summary(self):
        result = ValidationResult()
        result.add_error("test", 0, "field", "Test error")
        result.add_warning("test", 1, "field", "Test warning")
        summary = result.summary()
        assert summary["is_valid"] is False
        assert summary["error_count"] == 1
        assert summary["warning_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
