#!/usr/bin/env python3
"""Comprehensive boundary case validation for Phase 2."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from datetime import date, timedelta
from src.data_loader import load_inventory_data
from src.data_quality import validate_inventory_data
from src.risk_engine import RiskCalculator, apply_risk_calculations

print("=" * 80)
print("PHASE 2 BOUNDARY CASE VALIDATION")
print("=" * 80)

ref_date = date(2026, 9, 15)
calc = RiskCalculator(reference_date=ref_date)

# Define test cases
test_cases = [
    ("Already Expired", "2026-09-01", 100, 50, 500, "No", "EXPIRED", "CRITICAL", 100),
    ("Expiring Today", "2026-09-15", 100, 50, 500, "No", "EXPIRING_SOON", "LOW", 15),
    ("Expiring in 30 days (boundary)", "2026-10-15", 100, 50, 500, "No", "EXPIRING_SOON", "LOW", 15),
    ("Expiring after 30 days", "2026-10-16", 100, 50, 500, "No", "SAFE", "LOW", 15),
    ("Zero Stock", "2027-06-15", 0, 50, 500, "No", "SAFE", "HIGH", None),
    ("Stock = Reorder Level", "2027-06-15", 50, 50, 500, "No", "SAFE", "LOW", 15),
    ("Stock Above Maximum", "2027-06-15", 600, 50, 500, "No", "SAFE", "HIGH", None),
    ("Missing Expiry Date", None, 100, 50, 500, "No", "UNKNOWN", "MEDIUM", None),
    ("Negative Stock", "2027-06-15", -10, 50, 500, "No", "SAFE", "HIGH", None),
]

print("\n1. EXPIRY STATUS BOUNDARY TESTS")
print("-" * 80)

test_data_expiry = {
    "Batch_ID": [f"EXP-{i:03d}" for i in range(len(test_cases[:4]))],
    "Medicine_Name": ["Test"] * 4,
    "Expiry_Date": ["2026-09-01", "2026-09-15", "2026-10-15", "2026-10-16"],
    "Current_Stock": [100, 100, 100, 100],
    "Reorder_Level": [50, 50, 50, 50],
    "Maximum_Stock": [500, 500, 500, 500],
    "Unit_Price": [10.0] * 4,
    "Critical_Medicine": ["No"] * 4,
}

df_expiry = pd.DataFrame(test_data_expiry)
df_expiry_risks = apply_risk_calculations(df_expiry, reference_date=ref_date)

results = [
    ("Already Expired (2026-09-01)", df_expiry_risks.iloc[0]),
    ("Expiring Today (2026-09-15)", df_expiry_risks.iloc[1]),
    ("Expiring in 30 days (2026-10-15)", df_expiry_risks.iloc[2]),
    ("Expiring after 30 days (2026-10-16)", df_expiry_risks.iloc[3]),
]

for label, row in results:
    status = row["Expiry_Status"]
    days = row["Days_To_Expiry"]
    print(f"  ✓ {label}")
    print(f"    Days to expiry: {days}, Status: {status}")
    if label == "Already Expired (2026-09-01)":
        assert status == "EXPIRED", f"Expected EXPIRED, got {status}"
        assert days < 0, f"Expected negative days, got {days}"
    elif label == "Expiring Today (2026-09-15)":
        assert status == "EXPIRING_SOON", f"Expected EXPIRING_SOON, got {status}"
        assert days == 0, f"Expected 0 days, got {days}"
    elif label == "Expiring in 30 days (2026-10-15)":
        assert status == "EXPIRING_SOON", f"Expected EXPIRING_SOON, got {status}"
        assert days == 30, f"Expected 30 days, got {days}"
    elif label == "Expiring after 30 days (2026-10-16)":
        assert status == "SAFE", f"Expected SAFE, got {status}"
        assert days == 31, f"Expected 31 days, got {days}"

print("\n2. STOCK STATUS BOUNDARY TESTS")
print("-" * 80)

test_data_stock = {
    "Batch_ID": ["STK-001", "STK-002", "STK-003"],
    "Medicine_Name": ["Test"] * 3,
    "Expiry_Date": ["2027-06-15"] * 3,
    "Current_Stock": [0, 50, 600],
    "Reorder_Level": [50, 50, 500],
    "Maximum_Stock": [500, 500, 500],
    "Unit_Price": [10.0] * 3,
    "Critical_Medicine": ["No"] * 3,
}

df_stock = pd.DataFrame(test_data_stock)
df_stock_risks = apply_risk_calculations(df_stock, reference_date=ref_date)

stock_results = [
    ("Zero Stock (current=0, reorder=50)", df_stock_risks.iloc[0], "LOW_STOCK"),
    ("Stock at Reorder Level (current=50, reorder=50)", df_stock_risks.iloc[1], "NORMAL"),
    ("Stock Above Maximum (current=600, max=500)", df_stock_risks.iloc[2], "OVERSTOCK"),
]

for label, row, expected_status in stock_results:
    status = row["Stock_Status"]
    print(f"  ✓ {label}")
    print(f"    Status: {status}")
    assert status == expected_status, f"Expected {expected_status}, got {status}"

print("\n3. CRITICAL MEDICINE + LOW STOCK INTERACTION")
print("-" * 80)

test_data_critical = {
    "Batch_ID": ["CRIT-001", "CRIT-002"],
    "Medicine_Name": ["Penicillin", "Aspirin"],
    "Expiry_Date": ["2027-06-15", "2027-06-15"],
    "Current_Stock": [30, 30],
    "Reorder_Level": [100, 100],
    "Maximum_Stock": [500, 500],
    "Unit_Price": [15.0, 10.0],
    "Critical_Medicine": ["Yes", "No"],
}

df_critical = pd.DataFrame(test_data_critical)
df_critical_risks = apply_risk_calculations(df_critical, reference_date=ref_date)

print(f"  ✓ Critical Medicine with Low Stock (Penicillin)")
print(f"    Stock Status: {df_critical_risks.iloc[0]['Stock_Status']}")
print(f"    Risk Level: {df_critical_risks.iloc[0]['Risk_Level']}")
assert df_critical_risks.iloc[0]['Risk_Level'] == "CRITICAL", "Critical medicine with low stock should be CRITICAL"

print(f"  ✓ Non-Critical Medicine with Low Stock (Aspirin)")
print(f"    Stock Status: {df_critical_risks.iloc[1]['Stock_Status']}")
print(f"    Risk Level: {df_critical_risks.iloc[1]['Risk_Level']}")
assert df_critical_risks.iloc[1]['Risk_Level'] == "HIGH", "Non-critical medicine with low stock should be HIGH"

print("\n4. MISSING EXPIRY DATE HANDLING")
print("-" * 80)

test_data_missing = {
    "Batch_ID": ["MISS-001"],
    "Medicine_Name": ["Test"],
    "Expiry_Date": [None],
    "Current_Stock": [100],
    "Reorder_Level": [50],
    "Maximum_Stock": [500],
    "Unit_Price": [10.0],
    "Critical_Medicine": ["No"],
}

df_missing = pd.DataFrame(test_data_missing)
df_missing_risks = apply_risk_calculations(df_missing, reference_date=ref_date)

print(f"  ✓ Missing Expiry Date")
print(f"    Days to Expiry: {df_missing_risks.iloc[0]['Days_To_Expiry']}")
print(f"    Expiry Status: {df_missing_risks.iloc[0]['Expiry_Status']}")
print(f"    Risk Level: {df_missing_risks.iloc[0]['Risk_Level']}")
assert df_missing_risks.iloc[0]['Expiry_Status'] == "UNKNOWN"
assert df_missing_risks.iloc[0]['Risk_Level'] == "MEDIUM"

print("\n5. NEGATIVE STOCK HANDLING")
print("-" * 80)

test_data_negative = {
    "Batch_ID": ["NEG-001"],
    "Medicine_Name": ["Test"],
    "Expiry_Date": ["2027-06-15"],
    "Current_Stock": [-10],
    "Reorder_Level": [50],
    "Maximum_Stock": [500],
    "Unit_Price": [10.0],
    "Critical_Medicine": ["No"],
}

df_negative = pd.DataFrame(test_data_negative)
df_negative_risks = apply_risk_calculations(df_negative, reference_date=ref_date)

print(f"  ✓ Negative Stock Value (-10)")
print(f"    Stock Status: {df_negative_risks.iloc[0]['Stock_Status']}")
print(f"    Risk Level: {df_negative_risks.iloc[0]['Risk_Level']}")
assert df_negative_risks.iloc[0]['Stock_Status'] == "LOW_STOCK"
assert df_negative_risks.iloc[0]['Risk_Level'] == "HIGH"

print("\n6. DUPLICATE BATCH_ID DETECTION")
print("-" * 80)

test_data_duplicate = {
    "Batch_ID": ["DUP-001", "DUP-001"],
    "Medicine_Name": ["Test", "Test"],
    "Expiry_Date": ["2027-06-15", "2027-06-15"],
    "Current_Stock": [100, 100],
    "Reorder_Level": [50, 50],
    "Maximum_Stock": [500, 500],
    "Unit_Price": [10.0, 10.0],
    "Critical_Medicine": ["No", "No"],
}

df_duplicate = pd.DataFrame(test_data_duplicate)
validation = validate_inventory_data(df_duplicate)

print(f"  ✓ Duplicate Batch_ID Detection")
print(f"    Warnings generated: {len(validation.warnings)}")
print(f"    Warning type: {validation.warnings[0]['category']}")
assert len(validation.warnings) > 0, "Should detect duplicates"
assert validation.warnings[0]['category'] == "duplicate_batch_id"

print("\n7. INVALID DATE HANDLING")
print("-" * 80)

test_data_invalid_date = {
    "Batch_ID": ["INV-001", "INV-002"],
    "Medicine_Name": ["Test", "Test"],
    "Expiry_Date": ["2026-13-45", "invalid-date"],
    "Current_Stock": [100, 100],
    "Reorder_Level": [50, 50],
    "Maximum_Stock": [500, 500],
    "Unit_Price": [10.0, 10.0],
    "Critical_Medicine": ["No", "No"],
}

df_invalid = pd.DataFrame(test_data_invalid_date)
validation = validate_inventory_data(df_invalid)

print(f"  ✓ Invalid Date Formats")
print(f"    Errors detected: {len(validation.errors)}")
for error in validation.errors:
    if "Expiry_Date" in error['column']:
        print(f"    Error: {error['message']}")
        assert "Invalid date format" in error['message'] or "Missing date" in error['message']

print("\n8. EXPIRED + LOW STOCK INTERACTION (CRITICAL)")
print("-" * 80)

test_data_expired_low = {
    "Batch_ID": ["ELP-001"],
    "Medicine_Name": ["Critical Drug"],
    "Expiry_Date": ["2026-09-01"],  # -14 days
    "Current_Stock": [20],
    "Reorder_Level": [100],
    "Maximum_Stock": [500],
    "Unit_Price": [15.0],
    "Critical_Medicine": ["Yes"],
}

df_expired_low = pd.DataFrame(test_data_expired_low)
df_expired_low_risks = apply_risk_calculations(df_expired_low, reference_date=ref_date)

print(f"  ✓ Expired + Low Stock (CRITICAL condition)")
print(f"    Days to Expiry: {df_expired_low_risks.iloc[0]['Days_To_Expiry']}")
print(f"    Expiry Status: {df_expired_low_risks.iloc[0]['Expiry_Status']}")
print(f"    Stock Status: {df_expired_low_risks.iloc[0]['Stock_Status']}")
print(f"    Risk Level: {df_expired_low_risks.iloc[0]['Risk_Level']}")
print(f"    Risk Score: {df_expired_low_risks.iloc[0]['Risk_Score']}")
assert df_expired_low_risks.iloc[0]['Risk_Level'] == "CRITICAL"
assert df_expired_low_risks.iloc[0]['Risk_Score'] == 100

print("\n9. EXPIRING SOON + LOW STOCK INTERACTION (CRITICAL)")
print("-" * 80)

test_data_expiring_low = {
    "Batch_ID": ["ESL-001"],
    "Medicine_Name": ["Antibiotic"],
    "Expiry_Date": ["2026-10-01"],  # +16 days (EXPIRING_SOON)
    "Current_Stock": [20],
    "Reorder_Level": [100],
    "Maximum_Stock": [500],
    "Unit_Price": [15.0],
    "Critical_Medicine": ["No"],
}

df_expiring_low = pd.DataFrame(test_data_expiring_low)
df_expiring_low_risks = apply_risk_calculations(df_expiring_low, reference_date=ref_date)

print(f"  ✓ Expiring Soon + Low Stock (CRITICAL condition #2)")
print(f"    Days to Expiry: {df_expiring_low_risks.iloc[0]['Days_To_Expiry']}")
print(f"    Expiry Status: {df_expiring_low_risks.iloc[0]['Expiry_Status']}")
print(f"    Stock Status: {df_expiring_low_risks.iloc[0]['Stock_Status']}")
print(f"    Risk Level: {df_expiring_low_risks.iloc[0]['Risk_Level']}")
assert df_expiring_low_risks.iloc[0]['Risk_Level'] == "CRITICAL"

print("\n10. INVENTORY VALUE CALCULATION")
print("-" * 80)

test_data_value = {
    "Batch_ID": ["VAL-001"],
    "Medicine_Name": ["Expensive Drug"],
    "Expiry_Date": ["2027-06-15"],
    "Current_Stock": [100],
    "Reorder_Level": [50],
    "Maximum_Stock": [500],
    "Unit_Price": [25.50],
    "Critical_Medicine": ["No"],
}

df_value = pd.DataFrame(test_data_value)
df_value_risks = apply_risk_calculations(df_value, reference_date=ref_date)

expected_value = 100 * 25.50
actual_value = df_value_risks.iloc[0]['Inventory_Value']
print(f"  ✓ Inventory Value Calculation")
print(f"    Current Stock: 100, Unit Price: $25.50")
print(f"    Expected Value: ${expected_value:,.2f}")
print(f"    Actual Value: ${actual_value:,.2f}")
assert actual_value == expected_value, f"Expected {expected_value}, got {actual_value}"

print("\n" + "=" * 80)
print("✓ ALL BOUNDARY CASES VALIDATED - NO ERRORS FOUND")
print("=" * 80)
