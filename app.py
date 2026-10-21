"""
Streamlit Web Control Center for FUNNOW Hotel Performance Automation.
Provides interactive inspection, email previews, batch triggers, and audit log exploration.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

from config import config
from data_loader import load_and_validate_hotels
from classifier import classify_all_hotels
from summarizer import generate_summary, generate_fallback_summary
from pipeline import run_pipeline
from audit_logger import AuditLogger

# Page configuration
st.set_page_config(
    page_title="FUNNOW Hotel Performance Engine",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .badge-doing-well {
        background-color: #DCFCE7;
        color: #15803D;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-needs-improvement {
        background-color: #FEF3C7;
        color: #B45309;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-data-check {
        background-color: #DBEAFE;
        color: #1D4ED8;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.image("https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=600&q=80", use_column_width=True)
st.sidebar.title("Automation Controls")

st.sidebar.markdown("### Safety Settings")
st.sidebar.info(f"**Test Email Target:**\n`{config.TEST_RECIPIENT_EMAIL}`")
st.sidebar.success("🛡️ **Live Partner Delivery:** BLOCKED\nAll emails safely routed to test inbox.")

dry_run = st.sidebar.checkbox("Dry Run Mode (Local Preview)", value=config.DRY_RUN)
force_resend = st.sidebar.checkbox("Force Re-dispatch (Bypass Duplicate Check)", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown("### Reporting Period")
period_key = st.sidebar.text_input("Period Key", value=config.REPORTING_PERIOD_KEY)
period_label = st.sidebar.text_input("Period Label", value=config.REPORTING_PERIOD_LABEL)

st.sidebar.markdown("---")
st.sidebar.markdown("### Optional AI API Key")
gemini_key = st.sidebar.text_input("Gemini API Key", value=config.GEMINI_API_KEY, type="password")
if gemini_key:
    config.GEMINI_API_KEY = gemini_key

# Load Live Data
@st.cache_data(ttl=60)
def get_live_data():
    valid, invalid = load_and_validate_hotels()
    classified, benchmarks = classify_all_hotels(valid)
    return valid, invalid, classified, benchmarks

try:
    valid_records, invalid_records, classified_hotels, benchmarks = get_live_data()
except Exception as e:
    st.error(f"Failed to fetch live Google Sheet data: {e}")
    st.stop()

# Header
st.markdown('<div class="main-header">🏨 FUNNOW Hotel Performance Automation Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Automated weekly Monday performance evaluation, AI briefings, and safe partner communications.</div>', unsafe_allow_html=True)

# Top Metric Cards
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Hotels Ingested", len(valid_records) + len(invalid_records))
col2.metric("Active Benchmark Cohort", benchmarks.sample_size)
col3.metric("Median Revenue", f"{config.CURRENCY_SYMBOL}{benchmarks.median_revenue:,.0f}")
col4.metric("Median Orders", f"{benchmarks.median_orders:.0f} bookings")
col5.metric("Benchmark AOV", f"{config.CURRENCY_SYMBOL}{benchmarks.benchmark_aov:,.2f}")

st.markdown("---")

tabs = st.tabs([
    "📊 Cohort & Classification",
    "✉️ Individual Email Preview",
    "🚀 Run Weekly Dispatch",
    "📜 Audit & Dispatch Log"
])

# ----------------- TAB 1: COHORT OVERVIEW -----------------
with tabs[0]:
    st.subheader("Hotel Cohort Performance & Classification")
    
    rows = []
    for h in classified_hotels:
        rows.append({
            "Hotel Brand": h.record.brandname,
            f"Revenue ({config.CURRENCY_SYMBOL})": f"{h.record.revenue:,.0f}",
            "Revenue vs Median": f"{'+' if h.revenue_vs_median_pct >= 0 else ''}{h.revenue_vs_median_pct}%",
            "Orders": h.record.orders,
            "Orders vs Median": f"{'+' if h.orders_vs_median_pct >= 0 else ''}{h.orders_vs_median_pct}%",
            f"AOV ({config.CURRENCY_SYMBOL})": f"{h.aov:,.2f}",
            "Classification": h.classification,
            "Partner Email": h.record.boss_email
        })
    df_display = pd.DataFrame(rows)
    st.dataframe(df_display, use_container_width=True)

    if invalid_records:
        st.warning(f"⚠️ {len(invalid_records)} records failed ingestion validation:")
        st.dataframe(pd.DataFrame([
            {"Hotel": r.raw_brandname, "Error": r.validation_error} for r in invalid_records
        ]))

# ----------------- TAB 2: EMAIL PREVIEW -----------------
with tabs[1]:
    st.subheader("Personalized Message Generator & Review")
    
    hotel_names = [h.record.brandname for h in classified_hotels]
    selected_name = st.selectbox("Select Hotel to Inspect", hotel_names)
    selected_hotel = next(h for h in classified_hotels if h.record.brandname == selected_name)

    c_left, c_right = st.columns([1, 2])
    with c_left:
        st.markdown(f"### {selected_hotel.record.brandname}")
        st.write(f"**Classification:** `{selected_hotel.classification}`")
        st.write(f"**Revenue:** {config.CURRENCY_SYMBOL}{selected_hotel.record.revenue:,.0f} ({selected_hotel.revenue_vs_median_pct:+.1f}% vs median)")
        st.write(f"**Orders:** {selected_hotel.record.orders} ({selected_hotel.orders_vs_median_pct:+.1f}% vs median)")
        st.write(f"**Average Order Value:** {config.CURRENCY_SYMBOL}{selected_hotel.aov:,.2f}")
        st.write(f"**Intended Partner Email:** `{selected_hotel.record.boss_email}`")
        st.write(f"**Effective Delivery Destination:** `{config.get_effective_recipient(selected_hotel.record.boss_email)[0]}`")
        
        st.markdown("**Performance Context Rules:**")
        for reason in selected_hotel.performance_reasons:
            st.markdown(f"- {reason}")

    with c_right:
        st.markdown("### Generated Email Preview")
        summary = generate_summary(selected_hotel, benchmarks, period_label)
        
        st.info(f"**Method:** `{summary.generation_method}` | **AI-Generated:** `{summary.is_ai_generated}`")
        st.text_input("Subject Line", value=summary.subject, disabled=True)
        st.text_area("Email Body", value=summary.body, height=350, disabled=True)

# ----------------- TAB 3: BATCH DISPATCH -----------------
with tabs[2]:
    st.subheader("Batch Execution Controller")
    st.markdown("""
    Click below to trigger the weekly automated workflow.
    - Validates all records
    - Applies deterministic classification rules
    - Generates personalized AI briefings (with deterministic fallback)
    - Enforces duplicate prevention for this reporting period
    - Dispatches to test inbox or writes local previews
    """)

    if st.button("🚀 Execute Weekly Monday Automation Run", type="primary"):
        with st.spinner("Processing weekly batch..."):
            result = run_pipeline(
                period_key=period_key,
                period_label=period_label,
                dry_run=dry_run,
                force_resend=force_resend
            )
        
        st.success(f"Batch completed successfully!")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Hotels Evaluated", result.total_raw_records)
        m2.metric("Dispatched / Previewed", result.successful_dispatches_count)
        m3.metric("Skipped Duplicates", result.skipped_duplicates_count)
        m4.metric("Errors", result.failed_dispatches_count)

        st.markdown("### Batch Results")
        res_rows = []
        for e in result.dispatch_results:
            res_rows.append({
                "Hotel": e.hotel_name,
                "Classification": e.classification,
                "Delivery Status": e.delivery_status,
                "Destination": e.actual_recipient,
                "Redirected": e.is_redirected,
                "Generation Method": e.generation_method,
                "Notes": e.error_details or "OK"
            })
        st.dataframe(pd.DataFrame(res_rows), use_container_width=True)

# ----------------- TAB 4: AUDIT LOG -----------------
with tabs[3]:
    st.subheader("Audit & Dispatch History")
    logger = AuditLogger()
    entries = logger.get_all_entries()

    if entries:
        audit_df = pd.DataFrame([e.model_dump() for e in entries])
        st.dataframe(audit_df.sort_values(by="timestamp", ascending=False), use_container_width=True)
        
        csv_data = audit_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Audit Log (CSV)",
            data=csv_data,
            file_name="funnow_dispatch_log.csv",
            mime="text/csv"
        )
    else:
        st.info("No dispatch history recorded yet. Run a batch from the 'Run Weekly Dispatch' tab.")
