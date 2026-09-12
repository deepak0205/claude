import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple

RISK_CONFIG = {
    "delay_threshold_days": 2,
    "temperature_weight": 50,
    "delay_weight": 25,
    "quantity_weight": 15,
    "missing_data_weight": 10,
}

RISK_LEVELS = {
    "LOW": (0, 29),
    "MEDIUM": (30, 59),
    "HIGH": (60, 79),
    "CRITICAL": (80, 100),
}

REQUIRED_COLUMNS = [
    "shipment_id",
    "product_id",
    "batch_id",
    "origin",
    "destination",
    "ship_date",
    "delivery_date",
    "temperature_min",
    "temperature_max",
    "allowed_temp_min",
    "allowed_temp_max",
    "delay_days",
    "quantity",
]


def validate_data(df: pd.DataFrame) -> Tuple[bool, str]:
    """Validate required columns and data integrity."""
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        return False, f"Missing required columns: {', '.join(missing_cols)}"

    if df.empty:
        return False, "DataFrame is empty"

    duplicates = df[df["shipment_id"].duplicated(keep=False)]
    if not duplicates.empty:
        dup_ids = duplicates["shipment_id"].unique()
        return False, f"Duplicate shipment IDs found: {', '.join(map(str, dup_ids))}"

    return True, "Validation passed"


def detect_temperature_excursion(row: pd.Series) -> bool:
    """Check if temperature exceeds allowed range."""
    try:
        if pd.isna(row["temperature_min"]) or pd.isna(row["allowed_temp_min"]):
            return False
        if pd.isna(row["temperature_max"]) or pd.isna(row["allowed_temp_max"]):
            return False
        return (
            row["temperature_min"] < row["allowed_temp_min"]
            or row["temperature_max"] > row["allowed_temp_max"]
        )
    except (TypeError, ValueError):
        return False


def detect_delay_risk(row: pd.Series) -> bool:
    """Check if delay exceeds threshold."""
    try:
        if pd.isna(row["delay_days"]):
            return False
        return row["delay_days"] > RISK_CONFIG["delay_threshold_days"]
    except (TypeError, ValueError):
        return False


def calculate_quantity_anomaly_threshold(quantities: pd.Series) -> Tuple[float, float]:
    """Calculate IQR-based quantity outlier bounds."""
    valid_quantities = quantities.dropna()
    if len(valid_quantities) == 0:
        return np.inf, -np.inf

    Q1 = valid_quantities.quantile(0.25)
    Q3 = valid_quantities.quantile(0.75)
    IQR = Q3 - Q1

    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    return lower_bound, upper_bound


def detect_quantity_anomaly(quantity: float, lower: float, upper: float) -> bool:
    """Check if quantity is an outlier based on IQR."""
    if pd.isna(quantity):
        return False
    return quantity < lower or quantity > upper


def calculate_risk_score(row: pd.Series, lower_qty: float, upper_qty: float) -> int:
    """Calculate composite risk score."""
    score = 0

    if detect_temperature_excursion(row):
        score += RISK_CONFIG["temperature_weight"]

    if detect_delay_risk(row):
        score += RISK_CONFIG["delay_weight"]

    if detect_quantity_anomaly(row["quantity"], lower_qty, upper_qty):
        score += RISK_CONFIG["quantity_weight"]

    if (
        pd.isna(row["temperature_min"])
        or pd.isna(row["temperature_max"])
        or pd.isna(row["delay_days"])
        or pd.isna(row["quantity"])
    ):
        score += RISK_CONFIG["missing_data_weight"]

    return min(score, 100)


def get_risk_level(score: int) -> str:
    """Classify risk based on score."""
    for level, (low, high) in RISK_LEVELS.items():
        if low <= score <= high:
            return level
    return "LOW"


def generate_risk_reason(
    row: pd.Series, lower_qty: float, upper_qty: float
) -> str:
    """Generate explainable reason for risk."""
    reasons = []

    if detect_temperature_excursion(row):
        reasons.append(
            f"Temperature excursion (min: {row['temperature_min']}°C vs allowed {row['allowed_temp_min']}°C, "
            f"max: {row['temperature_max']}°C vs allowed {row['allowed_temp_max']}°C)"
        )

    if detect_delay_risk(row):
        reasons.append(
            f"Delivery delayed by {row['delay_days']} days (threshold: {RISK_CONFIG['delay_threshold_days']} days)"
        )

    if detect_quantity_anomaly(row["quantity"], lower_qty, upper_qty):
        reasons.append(f"Unusual quantity {row['quantity']} (normal range: {lower_qty:.0f}-{upper_qty:.0f})")

    if not reasons:
        reasons.append("Minor risk factors or missing data")

    return "; ".join(reasons)


def analyze_shipments(df: pd.DataFrame) -> pd.DataFrame:
    """Perform complete risk analysis on shipments."""
    is_valid, msg = validate_data(df)
    if not is_valid:
        raise ValueError(f"Validation failed: {msg}")

    df = df.copy()

    lower_qty, upper_qty = calculate_quantity_anomaly_threshold(df["quantity"])

    df["temperature_excursion"] = df.apply(detect_temperature_excursion, axis=1)
    df["delay_risk"] = df.apply(detect_delay_risk, axis=1)
    df["quantity_risk"] = df.apply(
        lambda row: detect_quantity_anomaly(row["quantity"], lower_qty, upper_qty),
        axis=1,
    )
    df["risk_score"] = df.apply(
        lambda row: calculate_risk_score(row, lower_qty, upper_qty), axis=1
    )
    df["risk_level"] = df["risk_score"].apply(get_risk_level)
    df["risk_reason"] = df.apply(
        lambda row: generate_risk_reason(row, lower_qty, upper_qty), axis=1
    )

    return df


def get_summary_stats(df: pd.DataFrame) -> Dict:
    """Calculate summary statistics."""
    total_shipments = len(df)
    high_risk = len(df[df["risk_level"].isin(["HIGH", "CRITICAL"])])
    temp_excursions = df["temperature_excursion"].sum()

    return {
        "total_shipments": total_shipments,
        "high_risk_count": high_risk,
        "temperature_excursions": int(temp_excursions),
    }


def get_risk_distribution(df: pd.DataFrame) -> Dict:
    """Get distribution of risk levels."""
    return df["risk_level"].value_counts().to_dict()


def get_top_5_shipments(df: pd.DataFrame) -> pd.DataFrame:
    """Get top 5 highest risk shipments."""
    cols = [
        "shipment_id",
        "product_id",
        "destination",
        "risk_score",
        "risk_level",
        "risk_reason",
    ]
    return df.nlargest(5, "risk_score")[cols]


def generate_recommendation(df: pd.DataFrame) -> str:
    """Generate actionable recommendation based on analysis."""
    high_risk = df[df["risk_level"].isin(["HIGH", "CRITICAL"])]

    if len(high_risk) == 0:
        return "No major shipment-risk pattern was detected. Continue routine monitoring."

    temp_risk = high_risk["temperature_excursion"].sum()
    delay_risk = high_risk["delay_risk"].sum()
    qty_risk = high_risk["quantity_risk"].sum()

    reasons = []

    if temp_risk > 0:
        reasons.append(
            "Temperature excursions are the primary risk driver. Review affected shipments and verify cold-chain handling."
        )

    if delay_risk > 0:
        reasons.append(
            "Delivery delays are a significant risk driver. Review affected routes and investigate recurring delivery bottlenecks."
        )

    if qty_risk > 0:
        reasons.append(
            "Unusual shipment quantities were detected. Review affected shipments against expected product and batch quantities."
        )

    return " ".join(reasons) if reasons else "Review high-risk shipments for compliance."
