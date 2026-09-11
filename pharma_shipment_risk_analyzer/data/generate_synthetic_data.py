import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)


def generate_synthetic_data(num_samples: int = 50) -> pd.DataFrame:
    """Generate deterministic synthetic pharma shipment data."""
    data = {
        "shipment_id": [f"SHIP-{1000+i}" for i in range(num_samples)],
        "product_id": [f"PROD-{100 + (i % 5)}" for i in range(num_samples)],
        "batch_id": [f"BATCH-{5000 + (i % 10)}" for i in range(num_samples)],
        "origin": np.random.choice(
            ["Warehouse_A", "Warehouse_B", "Warehouse_C"], num_samples
        ),
        "destination": np.random.choice(
            ["Hospital_X", "Hospital_Y", "Clinic_Z", "Facility_D"], num_samples
        ),
        "ship_date": [
            (datetime(2024, 1, 1) + timedelta(days=i % 90)).strftime("%Y-%m-%d")
            for i in range(num_samples)
        ],
        "delivery_date": [
            (
                datetime(2024, 1, 1)
                + timedelta(days=i % 90)
                + timedelta(days=2 + (i % 5))
            ).strftime("%Y-%m-%d")
            for i in range(num_samples)
        ],
        "temperature_min": np.round(
            np.random.normal(2, 1, num_samples), 1
        ),
        "temperature_max": np.round(
            np.random.normal(8, 1.5, num_samples), 1
        ),
        "allowed_temp_min": np.full(num_samples, 2.0),
        "allowed_temp_max": np.full(num_samples, 8.0),
        "delay_days": np.random.poisson(1.5, num_samples),
        "quantity": np.random.gamma(shape=2, scale=500, size=num_samples).astype(int),
    }

    df = pd.DataFrame(data)

    # Case 1: Normal shipment (indices 0-9)
    # Already handled by random generation

    # Case 2: Temperature excursion (indices 10-14)
    df.loc[10, "temperature_min"] = -2
    df.loc[11, "temperature_max"] = 12
    df.loc[12, "temperature_min"] = -1
    df.loc[13, "temperature_max"] = 15
    df.loc[14, "temperature_min"] = -3

    # Case 3: Delayed shipment (indices 15-19)
    df.loc[15, "delay_days"] = 5
    df.loc[16, "delay_days"] = 8
    df.loc[17, "delay_days"] = 6
    df.loc[18, "delay_days"] = 4
    df.loc[19, "delay_days"] = 7

    # Case 4: Quantity anomaly (indices 20-24)
    df.loc[20, "quantity"] = 10000
    df.loc[21, "quantity"] = 50
    df.loc[22, "quantity"] = 9500
    df.loc[23, "quantity"] = 100
    df.loc[24, "quantity"] = 8000

    # Case 5: Temperature + delay (indices 25-29)
    df.loc[25, "temperature_min"] = -1
    df.loc[25, "delay_days"] = 5
    df.loc[26, "temperature_max"] = 11
    df.loc[26, "delay_days"] = 4
    df.loc[27, "temperature_min"] = -2
    df.loc[27, "delay_days"] = 6
    df.loc[28, "temperature_max"] = 13
    df.loc[28, "delay_days"] = 3
    df.loc[29, "temperature_min"] = -1
    df.loc[29, "delay_days"] = 7

    # Case 6: Missing temperature (indices 30-34)
    df.loc[30, "temperature_min"] = np.nan
    df.loc[31, "temperature_max"] = np.nan
    df.loc[32, "temperature_min"] = np.nan
    df.loc[32, "temperature_max"] = np.nan
    df.loc[33, "temperature_min"] = np.nan
    df.loc[34, "temperature_max"] = np.nan

    # Case 7: Missing shipment ID (will be handled in validation)

    # Case 8: Extreme temperature (indices 35-36)
    df.loc[35, "temperature_min"] = -20
    df.loc[35, "temperature_max"] = 50

    # Case 9: Multiple high-risk (indices 37-39)
    df.loc[37, "temperature_min"] = -5
    df.loc[37, "delay_days"] = 10
    df.loc[37, "quantity"] = 15000
    df.loc[38, "temperature_max"] = 20
    df.loc[38, "delay_days"] = 8
    df.loc[39, "temperature_min"] = -3
    df.loc[39, "temperature_max"] = 18
    df.loc[39, "delay_days"] = 9

    return df


if __name__ == "__main__":
    df = generate_synthetic_data()
    df.to_excel("synthetic/test_shipments.xlsx", index=False)
    print(f"Generated {len(df)} synthetic records")
    print(df.head(10))
