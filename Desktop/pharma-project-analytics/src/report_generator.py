"""Report generation module for pharmaceutical inventory analysis."""

import pandas as pd
from datetime import datetime
from typing import Dict, Any
from . import analytics


def generate_executive_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate executive summary of inventory status.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        Dictionary with summary statistics
    """
    if len(df) == 0:
        return {"error": "Empty dataset"}

    # Get risk summary
    risk_dist = {}
    if "Risk_Level" in df.columns:
        risk_counts = df["Risk_Level"].value_counts().to_dict()
        risk_dist = {level: risk_counts.get(level, 0) for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]}

    # Get expiry summary
    expiry_dist = {}
    if "Expiry_Status" in df.columns:
        expiry_counts = df["Expiry_Status"].value_counts().to_dict()
        expiry_dist = {status: expiry_counts.get(status, 0) for status in ["EXPIRED", "EXPIRING_SOON", "SAFE", "UNKNOWN"]}

    # Get stock summary
    stock_dist = {}
    if "Stock_Status" in df.columns:
        stock_counts = df["Stock_Status"].value_counts().to_dict()
        stock_dist = {status: stock_counts.get(status, 0) for status in ["LOW_STOCK", "NORMAL", "OVERSTOCK", "UNKNOWN"]}

    # Get value summary
    value_summary = analytics.get_inventory_value_summary(df)

    return {
        "generated_at": datetime.now().isoformat(),
        "total_batches": len(df),
        "total_units": df["Current_Stock"].sum() if "Current_Stock" in df.columns else 0,
        "risk_distribution": risk_dist,
        "expiry_distribution": expiry_dist,
        "stock_distribution": stock_dist,
        "inventory_value": value_summary,
    }


def generate_critical_items_report(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate detailed report of critical items requiring immediate action.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        Dictionary with critical items and actions needed
    """
    critical_df = df[df.get("Risk_Level") == "CRITICAL"].copy() if "Risk_Level" in df.columns else pd.DataFrame()

    if len(critical_df) == 0:
        return {
            "critical_count": 0,
            "items": [],
            "message": "No critical items detected.",
        }

    items = []
    for idx, row in critical_df.iterrows():
        items.append({
            "batch_id": row.get("Batch_ID"),
            "medicine_name": row.get("Medicine_Name"),
            "expiry_status": row.get("Expiry_Status"),
            "stock_status": row.get("Stock_Status"),
            "days_to_expiry": row.get("Days_To_Expiry"),
            "current_stock": row.get("Current_Stock"),
            "reorder_level": row.get("Reorder_Level"),
            "recommended_action": row.get("Recommended_Action"),
            "warehouse": row.get("Warehouse"),
        })

    return {
        "critical_count": len(critical_df),
        "items": items,
        "message": f"{len(critical_df)} critical items require immediate attention.",
    }


def generate_expiry_report(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate expiry management report.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        Dictionary with expiry analysis and timeline
    """
    expiry_dist = analytics.get_expiry_distribution(df)
    timeline = analytics.get_expiry_timeline(df)

    timeline_summary = {}
    if len(timeline) > 0:
        period_counts = timeline["Expiry_Period"].value_counts().to_dict()
        for period in ["Expired", "Critical (0-7 days)", "Warning (8-30 days)", "Caution (31-90 days)", "Safe (90+ days)"]:
            timeline_summary[period] = period_counts.get(period, 0)

    return {
        "expiry_distribution": expiry_dist,
        "timeline": timeline_summary,
        "expired_count": expiry_dist.get("EXPIRED", 0),
        "expiring_soon_count": expiry_dist.get("EXPIRING_SOON", 0),
    }


def generate_stock_report(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate stock management report.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        Dictionary with stock analysis and recommendations
    """
    stock_dist = analytics.get_stock_distribution(df)
    reorder_recs = analytics.get_reorder_recommendations(df)

    reorder_items = []
    if len(reorder_recs) > 0:
        for idx, row in reorder_recs.iterrows():
            reorder_items.append({
                "batch_id": row.get("Batch_ID"),
                "medicine_name": row.get("Medicine_Name"),
                "current_stock": row.get("Current_Stock"),
                "reorder_level": row.get("Reorder_Level"),
                "suggested_order": row.get("Suggested_Order_Qty"),
                "priority": row.get("Priority"),
            })

    return {
        "stock_distribution": stock_dist,
        "low_stock_count": stock_dist.get("LOW_STOCK", 0),
        "overstock_count": stock_dist.get("OVERSTOCK", 0),
        "reorder_recommendations": reorder_items,
    }


def generate_warehouse_report(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate warehouse-wise inventory analysis.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        Dictionary with warehouse analysis
    """
    warehouse_analysis = analytics.get_warehouse_analysis(df)

    return {
        "warehouses": warehouse_analysis,
        "total_warehouse_count": len(warehouse_analysis),
    }


def generate_category_report(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate medicine category analysis.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        Dictionary with category-wise analysis
    """
    category_analysis = analytics.get_medicine_category_analysis(df)

    return {
        "categories": category_analysis,
        "total_categories": len(category_analysis),
    }


def generate_full_report(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate comprehensive inventory report.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        Dictionary with complete report data
    """
    return {
        "generated_at": datetime.now().isoformat(),
        "executive_summary": generate_executive_summary(df),
        "critical_items": generate_critical_items_report(df),
        "expiry_management": generate_expiry_report(df),
        "stock_management": generate_stock_report(df),
        "warehouse_analysis": generate_warehouse_report(df),
        "category_analysis": generate_category_report(df),
    }
