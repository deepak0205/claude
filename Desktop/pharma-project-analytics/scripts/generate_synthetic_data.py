#!/usr/bin/env python3
"""Generate synthetic pharmaceutical inventory data for testing and development."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

today = datetime.now().date()

# Medicine catalog
medicines = [
    ("Aspirin", "Analgesic", "PharmaCorp"),
    ("Ibuprofen", "Analgesic", "MediServe"),
    ("Penicillin", "Antibiotic", "PharmaCorp"),
    ("Amoxicillin", "Antibiotic", "MediServe"),
    ("Lisinopril", "Antihypertensive", "CardioMed"),
    ("Metformin", "Antidiabetic", "DiabetesCare"),
    ("Amlodipine", "Antihypertensive", "CardioMed"),
    ("Omeprazole", "Gastric", "GutHealth"),
    ("Atorvastatin", "Cholesterol", "CardioMed"),
    ("Levothyroxine", "Thyroid", "Endocare"),
    ("Warfarin", "Anticoagulant", "BloodCare"),
    ("Clopidogrel", "Antiplatelet", "CardioMed"),
    ("Metoprolol", "Beta-blocker", "CardioMed"),
    ("Cetirizine", "Antihistamine", "AllergyCare"),
    ("Fluticasone", "Corticosteroid", "RespiratoryCare"),
]

warehouses = ["WH-North", "WH-South", "WH-Central", "WH-East", "WH-West"]
categories = ["Analgesic", "Antibiotic", "Antihypertensive", "Antidiabetic", "Cholesterol",
              "Thyroid", "Anticoagulant", "Antiplatelet", "Beta-blocker", "Antihistamine",
              "Corticosteroid", "Gastric"]

critical_medicines_list = ["Penicillin", "Warfarin", "Insulin", "Epinephrine", "Nitroglycerin"]

records = []

# Helper function to generate date variations
def generate_expiry_date_category(category):
    """Generate expiry dates with specific categories for test coverage."""
    if category == "expired":
        # Expired 1-60 days ago
        days_past = random.randint(1, 60)
        return today - timedelta(days=days_past)
    elif category == "expiring_soon":
        # Expiring within 1-30 days
        days_to_expiry = random.randint(1, 30)
        return today + timedelta(days=days_to_expiry)
    elif category == "safe":
        # Safe, 31+ days to expiry
        days_to_expiry = random.randint(31, 365)
        return today + timedelta(days=days_to_expiry)
    else:
        # Random normal distribution
        days_to_expiry = random.randint(-30, 300)
        return today + timedelta(days=days_to_expiry)

# Generate test data with controlled distributions
test_scenarios = {
    "expired": 15,                    # 15 expired batches
    "expiring_soon": 25,              # 25 batches expiring within 30 days
    "safe": 140,                      # 140 batches with safe expiry
    "mixed": 20,                      # 20 random records for variation
}

batch_id = 1

# 1. Generate controlled test scenarios
for scenario, count in test_scenarios.items():
    for _ in range(count):
        med_name, cat, mfg = random.choice(medicines)

        # Generate expiry date based on scenario
        if scenario == "expired":
            expiry = generate_expiry_date_category("expired")
        elif scenario == "expiring_soon":
            expiry = generate_expiry_date_category("expiring_soon")
        elif scenario == "safe":
            expiry = generate_expiry_date_category("safe")
        else:
            expiry = generate_expiry_date_category("random")

        manufacturing = expiry - timedelta(days=random.randint(180, 730))

        # Stock levels - some normal, some low, some overstock
        stock_type = random.choices(["normal", "low", "overstock"], weights=[0.6, 0.25, 0.15])[0]
        reorder = random.randint(50, 200)
        max_stock = reorder * random.uniform(1.5, 3.0)

        if stock_type == "normal":
            current_stock = random.randint(int(reorder), int(max_stock))
        elif stock_type == "low":
            current_stock = random.randint(0, int(reorder - 1))
        else:  # overstock
            current_stock = random.randint(int(max_stock) + 1, int(max_stock * 1.5))

        is_critical = med_name in critical_medicines_list

        records.append({
            "Batch_ID": f"BATCH-{batch_id:04d}",
            "Medicine_Name": med_name,
            "Category": cat,
            "Manufacturer": mfg,
            "Manufacturing_Date": manufacturing.strftime("%Y-%m-%d"),
            "Expiry_Date": expiry.strftime("%Y-%m-%d"),
            "Current_Stock": int(current_stock),
            "Reorder_Level": reorder,
            "Maximum_Stock": int(max_stock),
            "Unit_Price": round(random.uniform(5, 150), 2),
            "Warehouse": random.choice(warehouses),
            "Critical_Medicine": "Yes" if is_critical else "No",
        })
        batch_id += 1

# 2. Add edge cases to test data quality
# Add records with missing values
missing_value_indices = random.sample(range(len(records)), 5)
for idx in missing_value_indices:
    field_to_remove = random.choice(["Current_Stock", "Expiry_Date", "Reorder_Level"])
    records[idx][field_to_remove] = None

# Add duplicate records
duplicate_count = 3
for i in range(duplicate_count):
    dup_record = records[i].copy()
    dup_record["Batch_ID"] = f"DUP-{records[i]['Batch_ID']}"
    records.append(dup_record)

# Add invalid date records
invalid_dates = [
    {"start": records[-1].copy(), "field": "Expiry_Date", "value": "2026-13-45"},
    {"start": records[-2].copy(), "field": "Manufacturing_Date", "value": "invalid-date"},
]
for invalid in invalid_dates:
    rec = invalid["start"]
    rec["Batch_ID"] = f"INVALID-{rec['Batch_ID']}"
    rec[invalid["field"]] = invalid["value"]
    records.append(rec)

# Add records with negative stock (data quality issue)
negative_records = random.sample(range(len(records) - 10), 2)
for idx in negative_records:
    records[idx]["Current_Stock"] = random.randint(-50, -1)

# Add records with invalid stock relationships (current > max)
invalid_stock_idx = random.sample(range(len(records) - 15), 2)
for idx in invalid_stock_idx:
    records[idx]["Current_Stock"] = records[idx]["Maximum_Stock"] * 2

# Create DataFrame
df = pd.DataFrame(records)

# Save to CSV
output_path = "/home/labuser/Desktop/pharma-project-analytics/data/pharma_inventory.csv"
df.to_csv(output_path, index=False)

print(f"✓ Synthetic dataset created: {output_path}")
print(f"  - Total records: {len(df)}")
print(f"  - Columns: {list(df.columns)}")
print(f"\nData Quality Summary:")
print(f"  - Expired batches: {len(df[df['Expiry_Date'] < today.strftime('%Y-%m-%d')])}")
print(f"  - Missing values: {df.isnull().sum().sum()}")
print(f"  - Records with issues (duplicates/invalid dates/negative stock): ~10")
