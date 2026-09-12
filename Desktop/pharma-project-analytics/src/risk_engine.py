"""Risk calculation engine for pharmaceutical inventory."""

import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Tuple, Any, Optional


class RiskCalculator:
    """Calculate risk scores and levels for pharmaceutical inventory."""

    def __init__(self, reference_date: Optional[date] = None):
        """
        Initialize risk calculator.

        Args:
            reference_date: Date to use for calculations (default: today)
        """
        self.reference_date = reference_date or datetime.now().date()

    def calculate_days_to_expiry(self, expiry_date_str: str) -> Optional[int]:
        """
        Calculate days until expiry from expiry date string.

        Args:
            expiry_date_str: Expiry date as YYYY-MM-DD string

        Returns:
            Number of days to expiry (negative if expired), or None if invalid
        """
        if pd.isna(expiry_date_str) or expiry_date_str == "":
            return None

        try:
            expiry_date = datetime.strptime(str(expiry_date_str), "%Y-%m-%d").date()
            days_to_expiry = (expiry_date - self.reference_date).days
            return days_to_expiry
        except (ValueError, TypeError):
            return None

    def get_expiry_status(self, days_to_expiry: Optional[int]) -> str:
        """
        Determine expiry status based on days to expiry.

        Status mapping:
        - EXPIRED: days_to_expiry < 0
        - EXPIRING_SOON: 0 <= days_to_expiry <= 30
        - SAFE: days_to_expiry > 30
        - UNKNOWN: if days_to_expiry is None

        Args:
            days_to_expiry: Days until expiry (can be negative)

        Returns:
            Status string: EXPIRED, EXPIRING_SOON, SAFE, or UNKNOWN
        """
        if days_to_expiry is None:
            return "UNKNOWN"
        if days_to_expiry < 0:
            return "EXPIRED"
        if days_to_expiry <= 30:
            return "EXPIRING_SOON"
        return "SAFE"

    def get_stock_status(self, current_stock: Optional[float], reorder_level: Optional[float],
                        max_stock: Optional[float]) -> str:
        """
        Determine stock status based on stock levels.

        Status mapping:
        - LOW_STOCK: current_stock < reorder_level
        - OVERSTOCK: current_stock > max_stock
        - NORMAL: reorder_level <= current_stock <= max_stock
        - UNKNOWN: if any value is invalid

        Args:
            current_stock: Current quantity in stock
            reorder_level: Minimum threshold for reordering
            max_stock: Maximum capacity

        Returns:
            Status string: LOW_STOCK, NORMAL, OVERSTOCK, or UNKNOWN
        """
        if pd.isna(current_stock) or pd.isna(reorder_level) or pd.isna(max_stock):
            return "UNKNOWN"

        try:
            current_stock = float(current_stock)
            reorder_level = float(reorder_level)
            max_stock = float(max_stock)

            if current_stock < reorder_level:
                return "LOW_STOCK"
            if current_stock > max_stock:
                return "OVERSTOCK"
            return "NORMAL"
        except (ValueError, TypeError):
            return "UNKNOWN"

    def calculate_inventory_value(self, current_stock: Optional[float],
                                 unit_price: Optional[float]) -> Optional[float]:
        """
        Calculate total inventory value for a batch.

        Args:
            current_stock: Current quantity
            unit_price: Price per unit

        Returns:
            Total value (current_stock * unit_price), or None if invalid
        """
        if pd.isna(current_stock) or pd.isna(unit_price):
            return None

        try:
            return float(current_stock) * float(unit_price)
        except (ValueError, TypeError):
            return None

    def is_critical_medicine(self, critical_medicine_flag: Any) -> bool:
        """
        Check if medicine is marked as critical.

        Args:
            critical_medicine_flag: Value from Critical_Medicine column

        Returns:
            True if critical, False otherwise
        """
        if pd.isna(critical_medicine_flag):
            return False

        return str(critical_medicine_flag).lower() in ["yes", "true", "1"]

    def calculate_risk_level(self, expiry_status: str, stock_status: str, is_critical: bool,
                           days_to_expiry: Optional[int] = None,
                           current_stock: Optional[float] = None,
                           reorder_level: Optional[float] = None) -> Tuple[str, str]:
        """
        Calculate risk level and determine recommended action.

        Risk levels (highest to lowest):
        - CRITICAL: Expired, OR (Expiring soon + Low stock), OR (Low stock + Critical medicine)
        - HIGH: Expiring soon, OR (Overstock), OR (Low stock)
        - MEDIUM: Low stock with adequate time to expiry
        - LOW: All other normal cases

        Args:
            expiry_status: EXPIRED, EXPIRING_SOON, SAFE, or UNKNOWN
            stock_status: LOW_STOCK, NORMAL, OVERSTOCK, or UNKNOWN
            is_critical: Whether medicine is marked critical
            days_to_expiry: Days to expiry (for detailed calculation)
            current_stock: Current stock quantity
            reorder_level: Reorder level threshold

        Returns:
            Tuple of (risk_level, recommended_action)
        """
        # CRITICAL RISK conditions
        if expiry_status == "EXPIRED":
            return "CRITICAL", "Immediate disposal required. Verify with pharmacist before action."

        if expiry_status == "EXPIRING_SOON" and stock_status == "LOW_STOCK":
            return "CRITICAL", "Expedite usage or disposal. Expiring soon with insufficient stock."

        if stock_status == "LOW_STOCK" and is_critical:
            return "CRITICAL", "Urgent reorder required. Critical medicine below reorder level."

        # HIGH RISK conditions
        if expiry_status == "EXPIRING_SOON":
            return "HIGH", "Plan usage within 30 days. Monitor for disposal if stock remains."

        if stock_status == "OVERSTOCK":
            return "HIGH", "Reduce stock by usage or redistribution. Verify purchase order."

        if stock_status == "LOW_STOCK":
            return "HIGH", "Reorder recommended. Current stock below reorder level."

        # MEDIUM RISK conditions
        if expiry_status == "UNKNOWN" or stock_status == "UNKNOWN":
            return "MEDIUM", "Data quality issue detected. Verify record before action."

        # LOW RISK (normal state)
        return "LOW", "No action required. Stock and expiry within normal ranges."

    def calculate_risk_score(self, risk_level: str, expiry_status: str, stock_status: str,
                            days_to_expiry: Optional[int] = None) -> int:
        """
        Calculate numeric risk score (0-100) for ranking and visualization.

        Scoring:
        - CRITICAL: 90-100
        - HIGH: 60-89
        - MEDIUM: 30-59
        - LOW: 0-29

        Args:
            risk_level: CRITICAL, HIGH, MEDIUM, or LOW
            expiry_status: EXPIRED, EXPIRING_SOON, SAFE, or UNKNOWN
            stock_status: LOW_STOCK, NORMAL, OVERSTOCK, or UNKNOWN
            days_to_expiry: Days to expiry for fine-tuning

        Returns:
            Risk score 0-100
        """
        if risk_level == "CRITICAL":
            if expiry_status == "EXPIRED":
                return 100
            return 90

        if risk_level == "HIGH":
            if expiry_status == "EXPIRING_SOON":
                return 75
            if stock_status == "OVERSTOCK":
                return 70
            if stock_status == "LOW_STOCK":
                return 80
            return 60

        if risk_level == "MEDIUM":
            return 45

        return 15  # LOW


def calculate_risk_for_batch(row: pd.Series, calculator: RiskCalculator) -> Dict[str, Any]:
    """
    Calculate all risk metrics for a single batch record.

    Args:
        row: A pandas Series representing a batch record
        calculator: RiskCalculator instance

    Returns:
        Dictionary with calculated risk fields
    """
    days_to_expiry = calculator.calculate_days_to_expiry(row.get("Expiry_Date"))
    expiry_status = calculator.get_expiry_status(days_to_expiry)
    stock_status = calculator.get_stock_status(
        row.get("Current_Stock"),
        row.get("Reorder_Level"),
        row.get("Maximum_Stock")
    )
    is_critical = calculator.is_critical_medicine(row.get("Critical_Medicine"))
    inventory_value = calculator.calculate_inventory_value(
        row.get("Current_Stock"),
        row.get("Unit_Price")
    )

    risk_level, recommended_action = calculator.calculate_risk_level(
        expiry_status, stock_status, is_critical, days_to_expiry,
        row.get("Current_Stock"), row.get("Reorder_Level")
    )

    risk_score = calculator.calculate_risk_score(
        risk_level, expiry_status, stock_status, days_to_expiry
    )

    return {
        "Days_To_Expiry": days_to_expiry,
        "Expiry_Status": expiry_status,
        "Stock_Status": stock_status,
        "Inventory_Value": inventory_value,
        "Risk_Score": risk_score,
        "Risk_Level": risk_level,
        "Recommended_Action": recommended_action,
    }


def apply_risk_calculations(df: pd.DataFrame, reference_date: Optional[date] = None) -> pd.DataFrame:
    """
    Apply risk calculations to all batches in DataFrame.

    Args:
        df: Input DataFrame with inventory data
        reference_date: Date to use for calculations (default: today)

    Returns:
        DataFrame with added risk calculation columns
    """
    calculator = RiskCalculator(reference_date=reference_date)
    risk_data = []

    for idx, row in df.iterrows():
        risk_calc = calculate_risk_for_batch(row, calculator)
        risk_data.append(risk_calc)

    risk_df = pd.DataFrame(risk_data)
    result_df = pd.concat([df.reset_index(drop=True), risk_df], axis=1)

    return result_df


def get_critical_items(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter for critical-risk items requiring human review.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        Filtered DataFrame with only CRITICAL risk items
    """
    if "Risk_Level" not in df.columns:
        return pd.DataFrame()

    return df[df["Risk_Level"] == "CRITICAL"].copy()


def get_risk_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate summary statistics of risk levels in dataset.

    Args:
        df: DataFrame with risk calculations applied

    Returns:
        Dictionary with risk distribution and statistics
    """
    if "Risk_Level" not in df.columns:
        return {"error": "Risk calculations not applied"}

    risk_counts = df["Risk_Level"].value_counts().to_dict()
    risk_levels = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    summary = {}
    for level in risk_levels:
        summary[level] = risk_counts.get(level, 0)

    return {
        "total_items": len(df),
        "risk_distribution": summary,
        "critical_count": summary.get("CRITICAL", 0),
        "high_count": summary.get("HIGH", 0),
        "medium_count": summary.get("MEDIUM", 0),
        "low_count": summary.get("LOW", 0),
        "critical_percentage": (summary.get("CRITICAL", 0) / len(df) * 100) if len(df) > 0 else 0,
    }
