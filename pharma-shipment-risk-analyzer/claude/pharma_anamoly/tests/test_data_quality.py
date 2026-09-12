import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np
from src.validation import (
    validate_schema, check_nulls, check_duplicates,
    validate_quantities, profile_dataset
)
from src.data_generation import generate_all_data


def test_schema_validation():
    """Test schema validation."""
    data = generate_all_data()
    products = data["products"]

    valid, msg = validate_schema(products, ["product_id", "product_type"])
    assert valid, msg

    valid, msg = validate_schema(products, ["product_id", "nonexistent"])
    assert not valid, "Should fail on missing column"
    print("✓ Schema validation test passed")


def test_null_detection():
    """Test null detection."""
    df = pd.DataFrame({
        "col1": [1, 2, None, 4],
        "col2": ["a", "b", "c", "d"]
    })

    nulls = check_nulls(df)
    assert "col1" in nulls.index, "Should detect null in col1"
    assert nulls["col1"] == 1, "Should find 1 null"
    print("✓ Null detection test passed")


def test_duplicate_detection():
    """Test duplicate key detection."""
    df = pd.DataFrame({
        "batch_id": ["BATCH001", "BATCH001", "BATCH002"],
        "value": [100, 200, 300]
    })

    duplicates = check_duplicates(df, "batch_id")
    assert len(duplicates) == 2, "Should find 2 duplicate rows"
    print("✓ Duplicate detection test passed")


def test_quantity_validation():
    """Test quantity validation."""
    inventory = generate_all_data()["inventory"]

    issues = validate_quantities(inventory, ["quantity"])
    negative_count = (inventory["quantity"] < 0).sum()

    if negative_count == 0:
        assert len(issues) == 0, "Should have no issues"
    else:
        assert len(issues) > 0, "Should detect negative quantities"

    print("✓ Quantity validation test passed")


def test_profile_dataset():
    """Test dataset profiling."""
    data = generate_all_data()
    profile = profile_dataset(data["inventory"])

    assert profile["rows"] > 0, "Should have rows"
    assert profile["columns"] > 0, "Should have columns"
    assert "nulls" in profile, "Should calculate nulls"
    print("✓ Profile dataset test passed")


if __name__ == "__main__":
    test_schema_validation()
    test_null_detection()
    test_duplicate_detection()
    test_quantity_validation()
    test_profile_dataset()
    print("\n✅ All data quality tests passed!")
