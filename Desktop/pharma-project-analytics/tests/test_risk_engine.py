"""Unit tests for risk calculation engine."""

import pytest
import pandas as pd
from datetime import datetime, date, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.risk_engine import (
    RiskCalculator, calculate_risk_for_batch, apply_risk_calculations,
    get_critical_items, get_risk_summary
)


class TestRiskCalculatorDaysToExpiry:
    """Test days to expiry calculation."""

    def test_expired_batch(self):
        calc = RiskCalculator(reference_date=date(2026, 9, 15))
        days = calc.calculate_days_to_expiry("2026-09-01")
        assert days == -14

    def test_expiry_today(self):
        calc = RiskCalculator(reference_date=date(2026, 9, 15))
        days = calc.calculate_days_to_expiry("2026-09-15")
        assert days == 0

    def test_expiring_soon(self):
        calc = RiskCalculator(reference_date=date(2026, 9, 15))
        days = calc.calculate_days_to_expiry("2026-10-01")
        assert days == 16

    def test_safe_expiry(self):
        calc = RiskCalculator(reference_date=date(2026, 9, 15))
        days = calc.calculate_days_to_expiry("2027-03-15")
        assert days == 181

    def test_invalid_date_format(self):
        calc = RiskCalculator(reference_date=date(2026, 9, 15))
        days = calc.calculate_days_to_expiry("2026-13-45")
        assert days is None

    def test_missing_date(self):
        calc = RiskCalculator(reference_date=date(2026, 9, 15))
        days = calc.calculate_days_to_expiry(None)
        assert days is None


class TestRiskCalculatorExpiryStatus:
    """Test expiry status classification."""

    def test_expired_status(self):
        calc = RiskCalculator()
        status = calc.get_expiry_status(-10)
        assert status == "EXPIRED"

    def test_expiring_soon_boundary_0(self):
        calc = RiskCalculator()
        status = calc.get_expiry_status(0)
        assert status == "EXPIRING_SOON"

    def test_expiring_soon_boundary_30(self):
        calc = RiskCalculator()
        status = calc.get_expiry_status(30)
        assert status == "EXPIRING_SOON"

    def test_expiring_soon_mid_range(self):
        calc = RiskCalculator()
        status = calc.get_expiry_status(15)
        assert status == "EXPIRING_SOON"

    def test_safe_boundary_31(self):
        calc = RiskCalculator()
        status = calc.get_expiry_status(31)
        assert status == "SAFE"

    def test_safe_status(self):
        calc = RiskCalculator()
        status = calc.get_expiry_status(180)
        assert status == "SAFE"

    def test_unknown_status(self):
        calc = RiskCalculator()
        status = calc.get_expiry_status(None)
        assert status == "UNKNOWN"


class TestRiskCalculatorStockStatus:
    """Test stock status classification."""

    def test_low_stock_status(self):
        calc = RiskCalculator()
        status = calc.get_stock_status(20, 100, 500)
        assert status == "LOW_STOCK"

    def test_normal_stock_at_reorder_level(self):
        calc = RiskCalculator()
        status = calc.get_stock_status(100, 100, 500)
        assert status == "NORMAL"

    def test_normal_stock_mid_range(self):
        calc = RiskCalculator()
        status = calc.get_stock_status(250, 100, 500)
        assert status == "NORMAL"

    def test_normal_stock_at_max_level(self):
        calc = RiskCalculator()
        status = calc.get_stock_status(500, 100, 500)
        assert status == "NORMAL"

    def test_overstock_status(self):
        calc = RiskCalculator()
        status = calc.get_stock_status(600, 100, 500)
        assert status == "OVERSTOCK"

    def test_zero_stock(self):
        calc = RiskCalculator()
        status = calc.get_stock_status(0, 100, 500)
        assert status == "LOW_STOCK"

    def test_missing_values(self):
        calc = RiskCalculator()
        status = calc.get_stock_status(None, 100, 500)
        assert status == "UNKNOWN"
        status = calc.get_stock_status(100, None, 500)
        assert status == "UNKNOWN"
        status = calc.get_stock_status(100, 50, None)
        assert status == "UNKNOWN"


class TestRiskCalculatorInventoryValue:
    """Test inventory value calculation."""

    def test_valid_calculation(self):
        calc = RiskCalculator()
        value = calc.calculate_inventory_value(100, 10.50)
        assert value == 1050.0

    def test_zero_stock(self):
        calc = RiskCalculator()
        value = calc.calculate_inventory_value(0, 10.50)
        assert value == 0.0

    def test_zero_price(self):
        calc = RiskCalculator()
        value = calc.calculate_inventory_value(100, 0)
        assert value == 0.0

    def test_missing_stock(self):
        calc = RiskCalculator()
        value = calc.calculate_inventory_value(None, 10.50)
        assert value is None

    def test_missing_price(self):
        calc = RiskCalculator()
        value = calc.calculate_inventory_value(100, None)
        assert value is None


class TestRiskCalculatorCriticalMedicine:
    """Test critical medicine flag parsing."""

    def test_yes_flag(self):
        calc = RiskCalculator()
        is_critical = calc.is_critical_medicine("Yes")
        assert is_critical is True

    def test_no_flag(self):
        calc = RiskCalculator()
        is_critical = calc.is_critical_medicine("No")
        assert is_critical is False

    def test_true_flag(self):
        calc = RiskCalculator()
        is_critical = calc.is_critical_medicine("true")
        assert is_critical is True

    def test_false_flag(self):
        calc = RiskCalculator()
        is_critical = calc.is_critical_medicine("false")
        assert is_critical is False

    def test_missing_flag(self):
        calc = RiskCalculator()
        is_critical = calc.is_critical_medicine(None)
        assert is_critical is False


class TestRiskCalculatorRiskLevel:
    """Test risk level and recommended action calculation."""

    def test_critical_expired(self):
        calc = RiskCalculator()
        level, action = calc.calculate_risk_level("EXPIRED", "NORMAL", False)
        assert level == "CRITICAL"
        assert "disposal" in action.lower()

    def test_critical_expiring_soon_and_low_stock(self):
        calc = RiskCalculator()
        level, action = calc.calculate_risk_level("EXPIRING_SOON", "LOW_STOCK", False)
        assert level == "CRITICAL"

    def test_critical_low_stock_and_critical_medicine(self):
        calc = RiskCalculator()
        level, action = calc.calculate_risk_level("SAFE", "LOW_STOCK", True)
        assert level == "CRITICAL"
        assert "urgent" in action.lower() or "reorder" in action.lower()

    def test_high_expiring_soon(self):
        calc = RiskCalculator()
        level, action = calc.calculate_risk_level("EXPIRING_SOON", "NORMAL", False)
        assert level == "HIGH"

    def test_high_overstock(self):
        calc = RiskCalculator()
        level, action = calc.calculate_risk_level("SAFE", "OVERSTOCK", False)
        assert level == "HIGH"

    def test_high_low_stock_non_critical(self):
        calc = RiskCalculator()
        level, action = calc.calculate_risk_level("SAFE", "LOW_STOCK", False)
        assert level == "HIGH"

    def test_medium_unknown_data(self):
        calc = RiskCalculator()
        level, action = calc.calculate_risk_level("UNKNOWN", "NORMAL", False)
        assert level == "MEDIUM"

    def test_low_normal(self):
        calc = RiskCalculator()
        level, action = calc.calculate_risk_level("SAFE", "NORMAL", False)
        assert level == "LOW"


class TestRiskCalculatorRiskScore:
    """Test numeric risk score calculation."""

    def test_critical_expired_score(self):
        calc = RiskCalculator()
        score = calc.calculate_risk_score("CRITICAL", "EXPIRED", "NORMAL")
        assert score == 100

    def test_critical_non_expired_score(self):
        calc = RiskCalculator()
        score = calc.calculate_risk_score("CRITICAL", "EXPIRING_SOON", "LOW_STOCK")
        assert score == 90

    def test_high_expiring_soon_score(self):
        calc = RiskCalculator()
        score = calc.calculate_risk_score("HIGH", "EXPIRING_SOON", "NORMAL")
        assert 60 <= score <= 89

    def test_medium_score(self):
        calc = RiskCalculator()
        score = calc.calculate_risk_score("MEDIUM", "UNKNOWN", "NORMAL")
        assert score == 45

    def test_low_score(self):
        calc = RiskCalculator()
        score = calc.calculate_risk_score("LOW", "SAFE", "NORMAL")
        assert score == 15


class TestCalculateRiskForBatch:
    """Test complete batch risk calculation."""

    def test_normal_batch(self):
        calc = RiskCalculator(reference_date=date(2026, 9, 15))
        row = pd.Series({
            "Batch_ID": "BATCH-001",
            "Medicine_Name": "Aspirin",
            "Expiry_Date": "2027-03-15",
            "Current_Stock": 250,
            "Reorder_Level": 100,
            "Maximum_Stock": 500,
            "Unit_Price": 10.50,
            "Critical_Medicine": "No",
        })
        risk = calculate_risk_for_batch(row, calc)
        assert risk["Risk_Level"] == "LOW"
        assert risk["Days_To_Expiry"] == 181
        assert risk["Expiry_Status"] == "SAFE"
        assert risk["Stock_Status"] == "NORMAL"
        assert risk["Inventory_Value"] == 2625.0

    def test_expired_critical_batch(self):
        calc = RiskCalculator(reference_date=date(2026, 9, 15))
        row = pd.Series({
            "Batch_ID": "BATCH-002",
            "Medicine_Name": "Penicillin",
            "Expiry_Date": "2026-09-01",
            "Current_Stock": 50,
            "Reorder_Level": 100,
            "Maximum_Stock": 500,
            "Unit_Price": 15.00,
            "Critical_Medicine": "Yes",
        })
        risk = calculate_risk_for_batch(row, calc)
        assert risk["Risk_Level"] == "CRITICAL"
        assert risk["Days_To_Expiry"] == -14
        assert risk["Expiry_Status"] == "EXPIRED"


class TestApplyRiskCalculations:
    """Test batch risk calculations application."""

    def test_apply_to_dataframe(self):
        df = pd.DataFrame({
            "Batch_ID": ["BATCH-001", "BATCH-002"],
            "Medicine_Name": ["Aspirin", "Penicillin"],
            "Expiry_Date": ["2027-03-15", "2026-09-01"],
            "Current_Stock": [250, 50],
            "Reorder_Level": [100, 100],
            "Maximum_Stock": [500, 500],
            "Unit_Price": [10.50, 15.00],
            "Critical_Medicine": ["No", "Yes"],
        })
        ref_date = date(2026, 9, 15)
        result = apply_risk_calculations(df, reference_date=ref_date)

        assert "Risk_Level" in result.columns
        assert "Days_To_Expiry" in result.columns
        assert len(result) == 2
        assert result.loc[0, "Risk_Level"] == "LOW"
        assert result.loc[1, "Risk_Level"] == "CRITICAL"


class TestGetCriticalItems:
    """Test critical items filtering."""

    def test_filter_critical_items(self):
        df = pd.DataFrame({
            "Batch_ID": ["BATCH-001", "BATCH-002", "BATCH-003"],
            "Risk_Level": ["LOW", "CRITICAL", "HIGH"],
            "Medicine_Name": ["A", "B", "C"],
        })
        critical = get_critical_items(df)
        assert len(critical) == 1
        assert critical.iloc[0]["Batch_ID"] == "BATCH-002"


class TestGetRiskSummary:
    """Test risk summary generation."""

    def test_risk_summary(self):
        df = pd.DataFrame({
            "Batch_ID": ["BATCH-001", "BATCH-002", "BATCH-003", "BATCH-004"],
            "Risk_Level": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        })
        summary = get_risk_summary(df)

        assert summary["total_items"] == 4
        assert summary["critical_count"] == 1
        assert summary["high_count"] == 1
        assert summary["medium_count"] == 1
        assert summary["low_count"] == 1
        assert 24.0 <= summary["critical_percentage"] <= 26.0  # ~25%


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
