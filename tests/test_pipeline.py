"""
Comprehensive Test Suite for FUNNOW Hotel Performance Automation.
Explicitly validates all 10 requirements specified in the Technical Assignment.
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from config import Config
from data_loader import load_and_validate_hotels, HotelRecord
from classifier import (
    compute_benchmarks,
    classify_hotel,
    classify_all_hotels,
    BenchmarkStats,
    ClassifiedHotel
)
from summarizer import generate_summary, generate_fallback_summary, GeneratedSummary
from dispatcher import EmailDispatcher
from audit_logger import AuditLogger, DispatchEntry
from pipeline import run_pipeline


@pytest.fixture
def sample_raw_dataframe():
    """Provides a realistic sample dataset matching the live Google Sheet."""
    return pd.DataFrame([
        {"brandname": "Hotel Alpha", "revenue": "350,000", "Order": "80", "Boss Gmail": "alpha@example.com"},
        {"brandname": "Hotel Beta", "revenue": "200,000", "Order": "40", "Boss Gmail": "beta@example.com"},
        {"brandname": "Hotel Zero", "revenue": "0", "Order": "0", "Boss Gmail": "zero@example.com"},
        {"brandname": "Hotel Median", "revenue": "300,000", "Order": "60", "Boss Gmail": "median@example.com"},
    ])


# 1. Valid hotel record processing
def test_valid_hotel_record_processing(sample_raw_dataframe):
    valid, invalid = load_and_validate_hotels(custom_df=sample_raw_dataframe)
    assert len(valid) == 4
    assert len(invalid) == 0
    assert valid[0].brandname == "Hotel Alpha"
    assert valid[0].revenue == 350000.0
    assert valid[0].orders == 80


# 2. Correct performance classification
def test_correct_performance_classification():
    records = [
        HotelRecord(raw_brandname="H1", brandname="H1", revenue=400000, orders=90, boss_email="h1@test.com"),
        HotelRecord(raw_brandname="H2", brandname="H2", revenue=200000, orders=40, boss_email="h2@test.com"),
        HotelRecord(raw_brandname="H3", brandname="H3", revenue=300000, orders=60, boss_email="h3@test.com"),
    ]
    benchmarks = compute_benchmarks(records)
    # Medians: rev = 300,000, orders = 60
    assert benchmarks.median_revenue == 300000.0
    assert benchmarks.median_orders == 60.0

    c1 = classify_hotel(records[0], benchmarks)
    assert c1.classification == "Doing Well"

    c2 = classify_hotel(records[1], benchmarks)
    assert c2.classification == "Needs Improvement"

    c3 = classify_hotel(records[2], benchmarks)
    # Meets both medians
    assert c3.classification == "Doing Well"


# 3. Personalized summaries for different hotels
def test_personalized_summaries():
    records = [
        HotelRecord(raw_brandname="Alpha", brandname="Alpha", revenue=500000, orders=100, boss_email="a@test.com"),
        HotelRecord(raw_brandname="Beta", brandname="Beta", revenue=100000, orders=20, boss_email="b@test.com"),
    ]
    benchmarks = compute_benchmarks(records)
    c_alpha = classify_hotel(records[0], benchmarks)
    c_beta = classify_hotel(records[1], benchmarks)

    s_alpha = generate_summary(c_alpha, benchmarks, "Week 42")
    s_beta = generate_summary(c_beta, benchmarks, "Week 42")

    # Content must reflect individual names and performance tier
    assert "Alpha" in s_alpha.body
    assert "Strong Performance" in s_alpha.subject
    assert "Beta" in s_beta.body
    assert "Optimization Opportunities" in s_beta.subject


# 4. Zero revenue and zero orders (Data Check anomaly handling)
def test_zero_revenue_and_zero_orders():
    zero_record = HotelRecord(
        raw_brandname="Cape Cottage",
        brandname="Cape Cottage",
        revenue=0.0,
        orders=0,
        boss_email="cape@test.com",
        is_zero_data=True
    )
    benchmarks = BenchmarkStats(
        sample_size=5, median_revenue=300000, median_orders=60,
        mean_revenue=300000, mean_orders=60, benchmark_aov=5000
    )
    classified = classify_hotel(zero_record, benchmarks)
    assert classified.classification == "Data Check"
    
    summary = generate_summary(classified, benchmarks)
    assert "[Action Required]" in summary.subject
    assert "sync interruption" in summary.body.lower() or "verification" in summary.body.lower()


# 5. Invalid or missing fields
def test_invalid_or_missing_fields():
    dirty_df = pd.DataFrame([
        {"brandname": "", "revenue": "100000", "Order": "10", "Boss Gmail": "test@example.com"},  # Missing brand
        {"brandname": "Hotel Corrupt Rev", "revenue": "N/A", "Order": "10", "Boss Gmail": "test@example.com"},  # Bad rev
        {"brandname": "Hotel Negative", "revenue": "-500", "Order": "10", "Boss Gmail": "test@example.com"},  # Neg rev
    ])
    valid, invalid = load_and_validate_hotels(custom_df=dirty_df)
    assert len(valid) == 0
    assert len(invalid) == 3


# 6. Missing or invalid email addresses
def test_invalid_email_addresses():
    bad_email_df = pd.DataFrame([
        {"brandname": "Hotel Bad Email", "revenue": "100000", "Order": "10", "Boss Gmail": "not-an-email"},
        {"brandname": "Hotel Empty Email", "revenue": "100000", "Order": "10", "Boss Gmail": ""},
    ])
    valid, invalid = load_and_validate_hotels(custom_df=bad_email_df)
    assert len(valid) == 0
    assert len(invalid) == 2
    assert "Invalid email address format" in invalid[0].validation_error


# 7. LLM API failure triggers graceful deterministic fallback
def test_llm_api_failure_fallback():
    record = HotelRecord(raw_brandname="Test Hotel", brandname="Test Hotel", revenue=300000, orders=60, boss_email="test@example.com")
    benchmarks = BenchmarkStats(
        sample_size=1, median_revenue=300000, median_orders=60,
        mean_revenue=300000, mean_orders=60, benchmark_aov=5000
    )
    classified = classify_hotel(record, benchmarks)

    # Force error in LLM call
    with patch("summarizer.config.GEMINI_API_KEY", "dummy_key"):
        with patch("summarizer._generate_with_gemini", side_effect=Exception("API Quota Exceeded")):
            summary = generate_summary(classified, benchmarks)
            assert summary.is_ai_generated is False
            assert summary.generation_method == "FALLBACK_DETERMINISTIC"
            assert "API Quota Exceeded" in summary.error_message


# 8. Email delivery failure handling
def test_email_delivery_failure():
    dispatcher = EmailDispatcher(dry_run=False)
    record = HotelRecord(raw_brandname="H1", brandname="H1", revenue=100000, orders=20, boss_email="h1@test.com")
    classified = ClassifiedHotel(
        record=record, classification="Needs Improvement", aov=5000,
        revenue_vs_median_pct=-10, orders_vs_median_pct=-10,
        performance_reasons=[], coaching_theme=""
    )
    summary = GeneratedSummary(subject="Subj", body="Body", is_ai_generated=False, generation_method="TEST")

    # When SMTP is unconfigured or server fails
    with patch("dispatcher.config.SMTP_USER", "fake@gmail.com"):
        with patch("dispatcher.config.SMTP_PASSWORD", "fakepass"):
            with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("SMTP server unreachable")):
                status, recipient, err = dispatcher.dispatch(classified, summary)
                assert status == "FAILED"
                assert "SMTP server unreachable" in err


# 9. Duplicate execution for the same reporting period (Idempotency)
def test_duplicate_execution_prevention(tmp_path):
    logger = AuditLogger(log_dir=tmp_path)
    entry = DispatchEntry(
        timestamp="2026-10-22T00:00:00Z",
        dispatch_key="hotel alpha|2026-w42",
        hotel_name="Hotel Alpha",
        reporting_period="2026-W42",
        classification="Doing Well",
        original_recipient="boss@alpha.com",
        actual_recipient="amohamonoha@gmail.com",
        is_redirected=True,
        delivery_status="PREVIEW_ONLY",
        generation_method="FALLBACK_DETERMINISTIC",
        is_ai_generated=False,
        revenue=300000,
        orders=60
    )
    logger.record_dispatch(entry)

    # Key must be detected as dispatched
    assert logger.is_dispatched("Hotel Alpha", "2026-W42") is True
    assert logger.is_dispatched("Hotel Alpha", "2026-W43") is False


# 10. Successful delivery to test inbox (safe redirection verification)
def test_safe_redirection_to_test_inbox():
    cfg = Config(
        TEST_RECIPIENT_EMAIL="amohamonoha@gmail.com",
        ENABLE_LIVE_PARTNER_DELIVERY=False
    )
    dest, is_redirected = cfg.get_effective_recipient("real_partner@hotel.com")
    assert dest == "amohamonoha@gmail.com"
    assert is_redirected is True
