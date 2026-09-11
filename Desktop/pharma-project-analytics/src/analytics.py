"""Analytics module for pharmaceutical inventory data."""

import pandas as pd
from typing import Dict, List, Any, Optional


def get_expiry_distribution(df: pd.DataFrame) -> Dict[str, int]:
    """
    Get distribution of batches by expiry status.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        Dictionary with expiry status counts
    """
    if "Expiry_Status" not in df.columns:
        return {}

    distribution = df["Expiry_Status"].value_counts().to_dict()
    return {status: distribution.get(status, 0) for status in ["EXPIRED", "EXPIRING_SOON", "SAFE", "UNKNOWN"]}


def get_stock_distribution(df: pd.DataFrame) -> Dict[str, int]:
    """
    Get distribution of batches by stock status.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        Dictionary with stock status counts
    """
    if "Stock_Status" not in df.columns:
        return {}

    distribution = df["Stock_Status"].value_counts().to_dict()
    return {status: distribution.get(status, 0) for status in ["LOW_STOCK", "NORMAL", "OVERSTOCK", "UNKNOWN"]}


def get_medicine_category_analysis(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Analyze inventory by medicine category.

    Args:
        df: DataFrame with inventory data

    Returns:
        Dictionary with category-wise analysis
    """
    if "Category" not in df.columns or len(df) == 0:
        return {}

    analysis = {}

    for category in df["Category"].unique():
        if pd.isna(category):
            continue

        category_df = df[df["Category"] == category]
        risk_counts = category_df["Risk_Level"].value_counts().to_dict() if "Risk_Level" in category_df.columns else {}

        analysis[str(category)] = {
            "total_batches": len(category_df),
            "total_units": category_df["Current_Stock"].sum() if "Current_Stock" in category_df.columns else 0,
            "critical_risk": risk_counts.get("CRITICAL", 0),
            "high_risk": risk_counts.get("HIGH", 0),
        }

    return analysis


def get_warehouse_analysis(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Analyze inventory by warehouse.

    Args:
        df: DataFrame with inventory data

    Returns:
        Dictionary with warehouse-wise analysis
    """
    if "Warehouse" not in df.columns or len(df) == 0:
        return {}

    analysis = {}

    for warehouse in df["Warehouse"].unique():
        if pd.isna(warehouse):
            continue

        warehouse_df = df[df["Warehouse"] == warehouse]
        risk_counts = warehouse_df["Risk_Level"].value_counts().to_dict() if "Risk_Level" in warehouse_df.columns else {}

        analysis[str(warehouse)] = {
            "total_batches": len(warehouse_df),
            "total_units": warehouse_df["Current_Stock"].sum() if "Current_Stock" in warehouse_df.columns else 0,
            "total_value": warehouse_df["Inventory_Value"].sum() if "Inventory_Value" in warehouse_df.columns else 0,
            "critical_risk": risk_counts.get("CRITICAL", 0),
            "high_risk": risk_counts.get("HIGH", 0),
        }

    return analysis


def get_critical_medicines_at_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get critical medicines with low stock or expiry issues.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        Filtered DataFrame with critical medicines at risk
    """
    if "Critical_Medicine" not in df.columns or "Risk_Level" not in df.columns:
        return pd.DataFrame()

    critical_df = df[df["Critical_Medicine"].astype(str).str.lower().isin(["yes", "true"])]
    at_risk = critical_df[critical_df["Risk_Level"].isin(["CRITICAL", "HIGH"])].copy()

    return at_risk.sort_values("Risk_Score", ascending=False)


def get_expiry_timeline(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get timeline of expiries grouped by time periods.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        DataFrame with expiry timeline sorted by days to expiry
    """
    if "Days_To_Expiry" not in df.columns:
        return pd.DataFrame()

    timeline_df = df[df["Days_To_Expiry"].notna()].copy()

    if len(timeline_df) == 0:
        return pd.DataFrame()

    timeline_df = timeline_df.sort_values("Days_To_Expiry")

    # Categorize into periods
    def categorize_period(days):
        if days < 0:
            return "Expired"
        elif days <= 7:
            return "Critical (0-7 days)"
        elif days <= 30:
            return "Warning (8-30 days)"
        elif days <= 90:
            return "Caution (31-90 days)"
        else:
            return "Safe (90+ days)"

    timeline_df["Expiry_Period"] = timeline_df["Days_To_Expiry"].apply(categorize_period)

    return timeline_df[["Batch_ID", "Medicine_Name", "Days_To_Expiry", "Expiry_Period", "Current_Stock", "Warehouse"]]


def get_reorder_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get medicines that need reordering.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        DataFrame with reorder recommendations sorted by urgency
    """
    if "Stock_Status" not in df.columns:
        return pd.DataFrame()

    low_stock_df = df[df["Stock_Status"] == "LOW_STOCK"].copy()

    if len(low_stock_df) == 0:
        return pd.DataFrame()

    # Calculate reorder quantity
    low_stock_df = low_stock_df.copy()
    low_stock_df["Suggested_Order_Qty"] = (
        low_stock_df["Maximum_Stock"] - low_stock_df["Current_Stock"]
    )

    # Prioritize by criticality and urgency
    low_stock_df["Priority"] = low_stock_df.apply(
        lambda row: 1 if row.get("Risk_Level") == "CRITICAL" else (
            2 if row.get("Risk_Level") == "HIGH" else 3
        ),
        axis=1
    )

    return low_stock_df[
        ["Batch_ID", "Medicine_Name", "Current_Stock", "Reorder_Level", "Suggested_Order_Qty", "Priority"]
    ].sort_values("Priority")


def get_inventory_value_summary(df: pd.DataFrame) -> Dict[str, float]:
    """
    Get total inventory value summary.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        Dictionary with value statistics
    """
    if "Inventory_Value" not in df.columns:
        return {}

    valid_values = df[df["Inventory_Value"].notna()]["Inventory_Value"]

    return {
        "total_value": valid_values.sum(),
        "average_batch_value": valid_values.mean() if len(valid_values) > 0 else 0,
        "max_batch_value": valid_values.max() if len(valid_values) > 0 else 0,
        "min_batch_value": valid_values.min() if len(valid_values) > 0 else 0,
    }
