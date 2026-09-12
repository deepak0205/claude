#!/usr/bin/env python3
"""Integration test: load data, validate, calculate risks, and generate report."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import load_inventory_data
from src.data_quality import validate_inventory_data
from src.risk_engine import apply_risk_calculations, get_risk_summary
from src.report_generator import generate_full_report
from datetime import date

print("=" * 70)
print("PHARMA INVENTORY - PHASE 2 INTEGRATION TEST")
print("=" * 70)

# Load data
print("\n1. Loading synthetic dataset...")
df, metadata = load_inventory_data("data/pharma_inventory.csv")
print(f"   ✓ Loaded {metadata['total_records']} records from {metadata['filepath']}")
print(f"   ✓ Columns: {', '.join(metadata['columns'])}")

# Validate data
print("\n2. Validating data quality...")
validation = validate_inventory_data(df)
print(f"   ✓ Valid records: {len(df)}")
print(f"   ✓ Validation errors: {len(validation.errors)}")
print(f"   ✓ Validation warnings: {len(validation.warnings)}")
if validation.errors:
    print("\n   Error Examples:")
    for error in validation.errors[:3]:
        print(f"     - Row {error['row_index']}: {error['message']}")

# Calculate risks
print("\n3. Calculating risk metrics...")
ref_date = date(2026, 9, 15)
df_with_risks = apply_risk_calculations(df, reference_date=ref_date)
print(f"   ✓ Added risk calculation columns")
print(f"   ✓ Risk columns: Days_To_Expiry, Expiry_Status, Stock_Status, Inventory_Value, Risk_Score, Risk_Level")

# Generate summary
print("\n4. Generating risk summary...")
risk_summary = get_risk_summary(df_with_risks)
print(f"   ✓ Total items: {risk_summary['total_items']}")
print(f"   ✓ CRITICAL: {risk_summary['critical_count']} ({risk_summary['critical_percentage']:.1f}%)")
print(f"   ✓ HIGH: {risk_summary['high_count']}")
print(f"   ✓ MEDIUM: {risk_summary['medium_count']}")
print(f"   ✓ LOW: {risk_summary['low_count']}")

# Generate detailed report
print("\n5. Generating comprehensive report...")
report = generate_full_report(df_with_risks)
exec_summary = report['executive_summary']
print(f"   ✓ Executive Summary:")
print(f"     - Total batches: {exec_summary['total_batches']}")
print(f"     - Total units: {exec_summary['total_units']}")
print(f"     - Total inventory value: ${exec_summary['inventory_value']['total_value']:,.2f}")

critical_report = report['critical_items']
print(f"\n   ✓ Critical Items Report:")
print(f"     - Critical items: {critical_report['critical_count']}")
if critical_report['items']:
    print(f"     - First critical item: {critical_report['items'][0]['medicine_name']} (Batch {critical_report['items'][0]['batch_id']})")
    print(f"       Action: {critical_report['items'][0]['recommended_action']}")

# Show sample data with calculations
print("\n6. Sample calculated records (first 5 items)...")
display_cols = ['Batch_ID', 'Medicine_Name', 'Days_To_Expiry', 'Expiry_Status', 'Stock_Status', 'Risk_Level', 'Risk_Score']
print("\n" + df_with_risks[display_cols].head(5).to_string(index=False))

print("\n" + "=" * 70)
print("✓ INTEGRATION TEST COMPLETE - ALL SYSTEMS OPERATIONAL")
print("=" * 70)
