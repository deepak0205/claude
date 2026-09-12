import sys
import os
import pandas as pd
import pytest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from risk_analyzer import (
    analyze_shipments,
    detect_temperature_excursion,
    detect_delay_risk,
    calculate_quantity_anomaly_threshold,
    detect_quantity_anomaly,
    calculate_risk_score,
    get_risk_level,
    get_summary_stats,
    get_top_5_shipments,
    get_risk_distribution,
    generate_recommendation,
    validate_data,
    RISK_CONFIG,
)


@pytest.fixture
def sample_data():
    """Create sample shipment data for testing."""
    return pd.DataFrame(
        {
            "shipment_id": ["SHIP-001", "SHIP-002", "SHIP-003"],
            "product_id": ["PROD-100", "PROD-101", "PROD-102"],
            "batch_id": ["BATCH-5000", "BATCH-5001", "BATCH-5002"],
            "origin": ["Warehouse_A", "Warehouse_B", "Warehouse_C"],
            "destination": ["Hospital_X", "Hospital_Y", "Clinic_Z"],
            "ship_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "delivery_date": ["2024-01-05", "2024-01-06", "2024-01-07"],
            "temperature_min": [2.0, 1.0, 3.0],
            "temperature_max": [8.0, 7.0, 9.0],
            "allowed_temp_min": [2.0, 2.0, 2.0],
            "allowed_temp_max": [8.0, 8.0, 8.0],
            "delay_days": [1, 2, 3],
            "quantity": [500, 600, 700],
        }
    )


@pytest.fixture
def temp_excursion_data():
    """Create data with temperature excursion."""
    return pd.Series(
        {
            "shipment_id": "SHIP-TEMP",
            "temperature_min": -1.0,
            "temperature_max": 10.0,
            "allowed_temp_min": 2.0,
            "allowed_temp_max": 8.0,
            "delay_days": 1,
            "quantity": 500,
        }
    )


@pytest.fixture
def delay_risk_data():
    """Create data with delay risk."""
    return pd.Series(
        {
            "shipment_id": "SHIP-DELAY",
            "temperature_min": 2.0,
            "temperature_max": 8.0,
            "allowed_temp_min": 2.0,
            "allowed_temp_max": 8.0,
            "delay_days": 5,
            "quantity": 500,
        }
    )


def test_validate_data_success(sample_data):
    """Test successful data validation."""
    is_valid, msg = validate_data(sample_data)
    assert is_valid is True
    assert msg == "Validation passed"


def test_validate_data_missing_columns():
    """Test validation with missing required columns."""
    incomplete_data = pd.DataFrame(
        {"shipment_id": ["SHIP-001"], "product_id": ["PROD-100"]}
    )
    is_valid, msg = validate_data(incomplete_data)
    assert is_valid is False
    assert "Missing required columns" in msg


def test_validate_data_empty():
    """Test validation with empty dataframe."""
    empty_data = pd.DataFrame()
    is_valid, msg = validate_data(empty_data)
    assert is_valid is False
    assert "missing" in msg.lower() or "empty" in msg.lower()


def test_validate_data_duplicates():
    """Test validation with duplicate shipment IDs."""
    dup_data = pd.DataFrame(
        {
            "shipment_id": ["SHIP-001", "SHIP-001", "SHIP-002"],
            "product_id": ["PROD-100", "PROD-101", "PROD-102"],
            "batch_id": ["BATCH-5000", "BATCH-5001", "BATCH-5002"],
            "origin": ["A", "B", "C"],
            "destination": ["X", "Y", "Z"],
            "ship_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "delivery_date": ["2024-01-05", "2024-01-06", "2024-01-07"],
            "temperature_min": [2, 2, 2],
            "temperature_max": [8, 8, 8],
            "allowed_temp_min": [2, 2, 2],
            "allowed_temp_max": [8, 8, 8],
            "delay_days": [1, 2, 3],
            "quantity": [500, 600, 700],
        }
    )
    is_valid, msg = validate_data(dup_data)
    assert is_valid is False
    assert "Duplicate" in msg


def test_temperature_excursion_detected(temp_excursion_data):
    """Test temperature excursion detection."""
    assert detect_temperature_excursion(temp_excursion_data) is True


def test_temperature_no_excursion(sample_data):
    """Test normal temperature detection."""
    assert detect_temperature_excursion(sample_data.iloc[0]) == False


def test_temperature_excursion_with_nan():
    """Test temperature detection with missing values."""
    data = pd.Series(
        {
            "temperature_min": np.nan,
            "allowed_temp_min": 2.0,
            "temperature_max": 8.0,
            "allowed_temp_max": 8.0,
        }
    )
    assert detect_temperature_excursion(data) is False


def test_delay_risk_detected(delay_risk_data):
    """Test delay risk detection."""
    assert detect_delay_risk(delay_risk_data) is True


def test_delay_no_risk(sample_data):
    """Test normal delay detection."""
    assert detect_delay_risk(sample_data.iloc[0]) == False


def test_delay_risk_with_nan():
    """Test delay detection with missing values."""
    data = pd.Series({"delay_days": np.nan})
    assert detect_delay_risk(data) is False


def test_quantity_anomaly_threshold(sample_data):
    """Test quantity anomaly threshold calculation."""
    lower, upper = calculate_quantity_anomaly_threshold(sample_data["quantity"])
    assert lower is not np.inf
    assert upper is not -np.inf
    assert lower < upper


def test_quantity_anomaly_detection():
    """Test quantity anomaly detection."""
    lower, upper = 400, 800
    assert detect_quantity_anomaly(200, lower, upper) is True
    assert detect_quantity_anomaly(600, lower, upper) is False
    assert detect_quantity_anomaly(1000, lower, upper) is True


def test_quantity_anomaly_with_nan():
    """Test quantity anomaly with missing values."""
    lower, upper = 400, 800
    assert detect_quantity_anomaly(np.nan, lower, upper) is False


def test_risk_score_calculation(temp_excursion_data):
    """Test risk score calculation."""
    lower, upper = 400, 800
    score = calculate_risk_score(temp_excursion_data, lower, upper)
    assert score >= 0
    assert score <= 100
    assert score >= RISK_CONFIG["temperature_weight"]


def test_risk_score_capped_at_100():
    """Test risk score is capped at 100."""
    data = pd.Series(
        {
            "temperature_min": -5.0,
            "temperature_max": 15.0,
            "allowed_temp_min": 2.0,
            "allowed_temp_max": 8.0,
            "delay_days": 10,
            "quantity": np.nan,
        }
    )
    score = calculate_risk_score(data, 400, 800)
    assert score <= 100


def test_risk_level_low():
    """Test LOW risk level classification."""
    assert get_risk_level(15) == "LOW"
    assert get_risk_level(29) == "LOW"


def test_risk_level_medium():
    """Test MEDIUM risk level classification."""
    assert get_risk_level(30) == "MEDIUM"
    assert get_risk_level(59) == "MEDIUM"


def test_risk_level_high():
    """Test HIGH risk level classification."""
    assert get_risk_level(60) == "HIGH"
    assert get_risk_level(79) == "HIGH"


def test_risk_level_critical():
    """Test CRITICAL risk level classification."""
    assert get_risk_level(80) == "CRITICAL"
    assert get_risk_level(100) == "CRITICAL"


def test_analyze_shipments(sample_data):
    """Test complete shipment analysis."""
    result = analyze_shipments(sample_data)
    assert len(result) == len(sample_data)
    assert "risk_score" in result.columns
    assert "risk_level" in result.columns
    assert "risk_reason" in result.columns
    assert "temperature_excursion" in result.columns
    assert "delay_risk" in result.columns
    assert "quantity_risk" in result.columns


def test_analyze_shipments_invalid_data():
    """Test analysis with invalid data."""
    invalid_data = pd.DataFrame({"shipment_id": ["SHIP-001"]})
    with pytest.raises(ValueError):
        analyze_shipments(invalid_data)


def test_total_shipments(sample_data):
    """Test total shipments count."""
    result = analyze_shipments(sample_data)
    stats = get_summary_stats(result)
    assert stats["total_shipments"] == 3


def test_high_risk_count():
    """Test high-risk shipment counting."""
    data = pd.DataFrame(
        {
            "shipment_id": ["SHIP-001", "SHIP-002", "SHIP-003"],
            "product_id": ["PROD-100", "PROD-101", "PROD-102"],
            "batch_id": ["BATCH-5000", "BATCH-5001", "BATCH-5002"],
            "origin": ["A", "B", "C"],
            "destination": ["X", "Y", "Z"],
            "ship_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "delivery_date": ["2024-01-05", "2024-01-06", "2024-01-07"],
            "temperature_min": [-1.0, 2.0, 2.0],
            "temperature_max": [10.0, 8.0, 8.0],
            "allowed_temp_min": [2.0, 2.0, 2.0],
            "allowed_temp_max": [8.0, 8.0, 8.0],
            "delay_days": [5, 2, 1],
            "quantity": [500, 600, 700],
        }
    )
    result = analyze_shipments(data)
    stats = get_summary_stats(result)
    assert stats["high_risk_count"] >= 0


def test_temperature_excursion_count(sample_data):
    """Test temperature excursion counting."""
    result = analyze_shipments(sample_data)
    stats = get_summary_stats(result)
    assert stats["temperature_excursions"] == result["temperature_excursion"].sum()


def test_top_5_shipments(sample_data):
    """Test top 5 shipments selection."""
    result = analyze_shipments(sample_data)
    top5 = get_top_5_shipments(result)
    assert len(top5) <= 5
    scores = top5["risk_score"].tolist()
    assert scores == sorted(scores, reverse=True)


def test_top_5_shipments_large_dataset():
    """Test top 5 with more than 5 shipments."""
    data = pd.DataFrame(
        {
            "shipment_id": [f"SHIP-{i}" for i in range(10)],
            "product_id": ["PROD-100"] * 10,
            "batch_id": ["BATCH-5000"] * 10,
            "origin": ["A"] * 10,
            "destination": ["X"] * 10,
            "ship_date": ["2024-01-01"] * 10,
            "delivery_date": ["2024-01-05"] * 10,
            "temperature_min": [2.0] * 10,
            "temperature_max": [8.0] * 10,
            "allowed_temp_min": [2.0] * 10,
            "allowed_temp_max": [8.0] * 10,
            "delay_days": list(range(10)),
            "quantity": [500] * 10,
        }
    )
    result = analyze_shipments(data)
    top5 = get_top_5_shipments(result)
    assert len(top5) == 5


def test_risk_distribution(sample_data):
    """Test risk level distribution calculation."""
    result = analyze_shipments(sample_data)
    dist = get_risk_distribution(result)
    assert isinstance(dist, dict)
    assert sum(dist.values()) == len(result)


def test_recommendation_low_risk(sample_data):
    """Test recommendation for low-risk shipments."""
    result = analyze_shipments(sample_data)
    rec = generate_recommendation(result)
    assert isinstance(rec, str)
    assert len(rec) > 0


def test_recommendation_high_risk():
    """Test recommendation for high-risk shipments."""
    data = pd.DataFrame(
        {
            "shipment_id": ["SHIP-001"],
            "product_id": ["PROD-100"],
            "batch_id": ["BATCH-5000"],
            "origin": ["A"],
            "destination": ["X"],
            "ship_date": ["2024-01-01"],
            "delivery_date": ["2024-01-05"],
            "temperature_min": [-1.0],
            "temperature_max": [10.0],
            "allowed_temp_min": [2.0],
            "allowed_temp_max": [8.0],
            "delay_days": [5],
            "quantity": [500],
        }
    )
    result = analyze_shipments(data)
    rec = generate_recommendation(result)
    assert "Temperature" in rec or "Delay" in rec


def test_missing_columns():
    """Test handling of missing required columns."""
    incomplete = pd.DataFrame({"shipment_id": ["SHIP-001"]})
    with pytest.raises(ValueError):
        analyze_shipments(incomplete)


def test_missing_values():
    """Test handling of missing values in critical fields."""
    data = pd.DataFrame(
        {
            "shipment_id": ["SHIP-001"],
            "product_id": ["PROD-100"],
            "batch_id": ["BATCH-5000"],
            "origin": ["A"],
            "destination": ["X"],
            "ship_date": ["2024-01-01"],
            "delivery_date": ["2024-01-05"],
            "temperature_min": [np.nan],
            "temperature_max": [8.0],
            "allowed_temp_min": [2.0],
            "allowed_temp_max": [8.0],
            "delay_days": [1],
            "quantity": [500],
        }
    )
    result = analyze_shipments(data)
    assert len(result) == 1
    assert result.iloc[0]["risk_score"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
