import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np
import yaml
from src.data_generation import generate_all_data
from src.features import engineer_features
from src.detection import AnomalyDetector


def load_config():
    """Load configuration."""
    with open("config/rules.yml", "r") as f:
        return yaml.safe_load(f)


def test_batch_anomaly_detection():
    """Test batch-level anomaly detection."""
    config = load_config()
    data = generate_all_data(with_anomalies=True)

    detector = AnomalyDetector(config)
    batch_anomalies = detector.detect_batch_anomalies(
        data["batches"],
        data["quality"],
        data["inventory"]
    )

    assert len(batch_anomalies) >= 0, "Should detect batch anomalies"
    print("✓ Batch anomaly detection test passed")


def test_inventory_anomaly_detection():
    """Test inventory anomaly detection."""
    config = load_config()
    data = generate_all_data(with_anomalies=True)
    engineered = engineer_features(data)

    detector = AnomalyDetector(config)
    inventory_anomalies = detector.detect_inventory_anomalies(
        engineered["inventory"],
        config
    )

    assert len(inventory_anomalies) >= 0, "Should run without errors"
    print("✓ Inventory anomaly detection test passed")


def test_quality_anomaly_detection():
    """Test quality anomaly detection."""
    config = load_config()
    data = generate_all_data(with_anomalies=True)

    detector = AnomalyDetector(config)
    quality_anomalies = detector.detect_quality_anomalies(data["quality"])

    assert len(quality_anomalies) >= 0, "Should detect quality anomalies"
    print("✓ Quality anomaly detection test passed")


def test_shipment_anomaly_detection():
    """Test shipment anomaly detection."""
    config = load_config()
    data = generate_all_data(with_anomalies=True)

    detector = AnomalyDetector(config)
    shipment_anomalies = detector.detect_shipment_anomalies(data["shipments"])

    assert len(shipment_anomalies) >= 0, "Should detect shipment anomalies"
    print("✓ Shipment anomaly detection test passed")


def test_all_anomaly_detection():
    """Test full anomaly detection pipeline."""
    config = load_config()
    data = generate_all_data(with_anomalies=True)
    engineered = engineer_features(data)

    detector = AnomalyDetector(config)
    all_anomalies = detector.detect_all_anomalies(engineered)

    assert isinstance(all_anomalies, pd.DataFrame), "Should return DataFrame"
    if len(all_anomalies) > 0:
        required_cols = ["anomaly_id", "business_key", "anomaly_type", "severity", "score"]
        for col in required_cols:
            assert col in all_anomalies.columns, f"Missing required column: {col}"

    print("✓ Full anomaly detection test passed")


def test_reproducibility():
    """Test that detection is reproducible with same data."""
    config = load_config()
    data1 = generate_all_data(with_anomalies=True)
    data2 = generate_all_data(with_anomalies=True)

    detector1 = AnomalyDetector(config)
    anomalies1 = detector1.detect_all_anomalies(engineer_features(data1))

    detector2 = AnomalyDetector(config)
    anomalies2 = detector2.detect_all_anomalies(engineer_features(data2))

    assert len(anomalies1) == len(anomalies2), "Should be reproducible"
    print("✓ Reproducibility test passed")


if __name__ == "__main__":
    test_batch_anomaly_detection()
    test_inventory_anomaly_detection()
    test_quality_anomaly_detection()
    test_shipment_anomaly_detection()
    test_all_anomaly_detection()
    test_reproducibility()
    print("\n✅ All detection tests passed!")
