import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from risk_analyzer import (
    analyze_shipments,
    get_summary_stats,
    get_risk_distribution,
    get_top_5_shipments,
    generate_recommendation,
)
import os

st.set_page_config(
    page_title="Pharma Shipment Risk Analyzer",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📦 Pharma Shipment Risk Analyzer")
st.markdown(
    """
    This application analyzes pharmaceutical shipments for temperature, delay, and quantity-based risks.
    **Disclaimer**: Results are for operational review only and require human validation.
    """
)

st.sidebar.header("Upload Data")
uploaded_file = st.sidebar.file_uploader(
    "Upload an Excel file (.xlsx or .xls)",
    type=["xlsx", "xls"],
    help="Expected columns: shipment_id, product_id, batch_id, origin, destination, "
    "ship_date, delivery_date, temperature_min, temperature_max, "
    "allowed_temp_min, allowed_temp_max, delay_days, quantity",
)

demo_option = st.sidebar.checkbox("Load Demo Data", value=False)

df = None

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.sidebar.success("✓ File loaded successfully")
    except Exception as e:
        st.sidebar.error(f"Error reading file: {str(e)}")

elif demo_option:
    demo_path = "data/synthetic/test_shipments.xlsx"
    if os.path.exists(demo_path):
        try:
            df = pd.read_excel(demo_path)
            st.sidebar.success("✓ Demo data loaded")
        except Exception as e:
            st.sidebar.error(f"Error loading demo data: {str(e)}")
    else:
        st.sidebar.warning("Demo data file not found. Please generate it first.")

if df is None:
    st.info("👈 Please upload an Excel file or load demo data to begin analysis.")
    st.stop()

try:
    analyzed_df = analyze_shipments(df)
    stats = get_summary_stats(analyzed_df)
    risk_dist = get_risk_distribution(analyzed_df)

except ValueError as e:
    st.error(f"Validation Error: {str(e)}")
    st.stop()
except Exception as e:
    st.error(f"Analysis Error: {str(e)}")
    st.stop()

st.subheader("📊 Summary Dashboard")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Shipments", stats["total_shipments"], help="All shipments in dataset")

with col2:
    st.metric(
        "High-Risk Shipments",
        stats["high_risk_count"],
        delta=f"{(stats['high_risk_count']/stats['total_shipments']*100):.1f}%",
        help="HIGH or CRITICAL risk level",
    )

with col3:
    st.metric(
        "Temperature Excursions",
        stats["temperature_excursions"],
        help="Shipments outside allowed temperature range",
    )

st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🔝 Top 5 Highest-Risk Shipments")
    top5 = get_top_5_shipments(analyzed_df)

    if not top5.empty:
        display_cols = ["shipment_id", "product_id", "destination", "risk_score", "risk_level"]
        st.dataframe(
            top5[display_cols],
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("📋 Detailed Risk Reasons"):
            for idx, row in top5.iterrows():
                st.write(f"**{row['shipment_id']}** (Score: {row['risk_score']}, Level: {row['risk_level']})")
                st.write(f"Reason: {row['risk_reason']}")
                st.divider()
    else:
        st.info("No shipments to display")

with col2:
    st.subheader("📈 Risk Distribution")

    if risk_dist:
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=list(risk_dist.keys()),
                    values=list(risk_dist.values()),
                    marker=dict(
                        colors=["#2ecc71", "#f39c12", "#e74c3c", "#c0392b"],
                        colorscale="Reds",
                    ),
                    hole=0.3,
                )
            ]
        )
        fig.update_layout(height=400, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data to display")

st.markdown("---")

st.subheader("💡 Recommendations")

recommendation = generate_recommendation(analyzed_df)
st.info(recommendation)

st.markdown("---")

st.subheader("📥 Full Analysis Results")

with st.expander("View All Shipments Analysis", expanded=False):
    display_cols = [
        "shipment_id",
        "product_id",
        "destination",
        "temperature_min",
        "temperature_max",
        "delay_days",
        "quantity",
        "risk_score",
        "risk_level",
    ]
    available_cols = [col for col in display_cols if col in analyzed_df.columns]

    st.dataframe(
        analyzed_df[available_cols].sort_values("risk_score", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")

st.markdown(
    """
    #### ℹ️ Risk Scoring Methodology
    - **Temperature Excursion**: +50 points (detected outside allowed range)
    - **Significant Delay**: +25 points (> 2 days)
    - **Quantity Anomaly**: +15 points (detected via IQR method)
    - **Missing Data**: +10 points (critical fields missing)

    **Risk Levels**:
    - 🟢 LOW (0–29): Normal operations
    - 🟡 MEDIUM (30–59): Monitor closely
    - 🟠 HIGH (60–79): Requires review
    - 🔴 CRITICAL (80–100): Immediate action needed

    **Note**: All results are for operational review only. Clinical decisions require human validation.
    """
)
