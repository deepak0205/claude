import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import yaml
from src.data_generation import generate_all_data
from src.features import engineer_features
from src.detection import AnomalyDetector
from src.scoring import (
    classify_severity, add_severity_classification,
    calculate_anomaly_statistics
)


def load_config():
    """Load configuration."""
    with open("config/rules.yml", "r") as f:
        return yaml.safe_load(f)


def test_severity_classification():
    """Test severity classification based on score."""
    config = load_config()

    assert classify_severity(0.95, config) == "CRITICAL"
    assert classify_severity(0.80, config) == "HIGH"
    assert classify_severity(0.70, config) == "MEDIUM"
    assert classify_severity(0.40, config) == "LOW"

    print("✓ Severity classification test passed")


def test_add_severity_classification():
    """Test adding severity to anomaly dataframe."""
    config = load_config()
    data = generate_all_data(with_anomalies=True)
    engineered = engineer_features(data)

    detector = AnomalyDetector(config)
    anomalies = detector.detect_all_anomalies(engineered)

    if len(anomalies) > 0:
        classified = add_severity_classification(anomalies, config)
        assert "calculated_severity" in classified.columns
        assert all(classified["calculated_severity"].isin(["LOW", "MEDIUM", "HIGH", "CRITICAL"]))

    print("✓ Add severity classification test passed")


def test_anomaly_statistics():
    """Test anomaly statistics calculation."""
    config = load_config()
    data = generate_all_data(with_anomalies=True)
    engineered = engineer_features(data)

    detector = AnomalyDetector(config)
    anomalies = detector.detect_all_anomalies(engineered)

    stats = calculate_anomaly_statistics(anomalies)

    assert "total_anomalies" in stats
    assert "by_severity" in stats
    assert "by_type" in stats
    assert "by_method" in stats
    assert "avg_score" in stats

    if len(anomalies) > 0:
        assert stats["total_anomalies"] == len(anomalies)
        assert stats["avg_score"] >= 0 and stats["avg_score"] <= 1

    print("✓ Anomaly statistics test passed")


def test_empty_dataframe_handling():
    """Test handling of empty dataframes."""
    config = load_config()
    empty_df = pd.DataFrame()

    stats = calculate_anomaly_statistics(empty_df)
    assert stats["total_anomalies"] == 0

    classified = add_severity_classification(empty_df, config)
    assert len(classified) == 0

    print("✓ Empty dataframe handling test passed")


if __name__ == "__main__":
    test_severity_classification()
    test_add_severity_classification()
    test_anomaly_statistics()
    test_empty_dataframe_handling()
    print("\n✅ All scoring tests passed!")
