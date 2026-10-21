"""
Orchestration pipeline executing the complete automated weekly cycle.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import pandas as pd
from pydantic import BaseModel

from config import config
from data_loader import load_and_validate_hotels, HotelRecord
from classifier import classify_all_hotels, ClassifiedHotel, BenchmarkStats
from summarizer import generate_summary, GeneratedSummary
from dispatcher import EmailDispatcher
from audit_logger import AuditLogger, DispatchEntry


class PipelineResult(BaseModel):
    """Execution summary for a pipeline run."""
    timestamp: str
    reporting_period_key: str
    reporting_period_label: str
    total_raw_records: int
    valid_records_count: int
    invalid_records_count: int
    benchmarks: BenchmarkStats
    processed_count: int
    skipped_duplicates_count: int
    successful_dispatches_count: int
    failed_dispatches_count: int
    classified_hotels: List[ClassifiedHotel]
    generated_summaries: Dict[str, GeneratedSummary]
    dispatch_results: List[DispatchEntry]


def run_pipeline(
    sheet_id: str = config.GOOGLE_SHEET_ID,
    sheet_name: str = config.GOOGLE_SHEET_TAB_DATA,
    custom_df: Optional[pd.DataFrame] = None,
    period_key: str = config.REPORTING_PERIOD_KEY,
    period_label: str = config.REPORTING_PERIOD_LABEL,
    dry_run: bool = config.DRY_RUN,
    force_resend: bool = False,
) -> PipelineResult:
    """
    Executes the end-to-end automation workflow:
    1. Ingestion & Validation
    2. Dynamic Benchmark & Classification
    3. AI/Fallback Message Generation
    4. Safe Dispatch (or Preview)
    5. Audit Logging with Idempotency Protection
    """
    run_timestamp = datetime.now(timezone.utc).isoformat()
    logger = AuditLogger()
    dispatcher = EmailDispatcher(dry_run=dry_run)

    # 1. Ingestion & Validation
    valid_records, invalid_records = load_and_validate_hotels(
        sheet_id=sheet_id,
        sheet_name=sheet_name,
        custom_df=custom_df
    )

    # 2. Classification & Benchmarks
    classified_hotels, benchmarks = classify_all_hotels(valid_records)

    generated_summaries: Dict[str, GeneratedSummary] = {}
    dispatch_results: List[DispatchEntry] = []

    processed_count = 0
    skipped_duplicates = 0
    success_count = 0
    fail_count = 0

    for hotel in classified_hotels:
        hotel_name = hotel.record.brandname
        dispatch_key = config.get_dispatch_key(hotel_name, period_key)

        # 3. Duplicate Prevention Check
        if not force_resend and logger.is_dispatched(hotel_name, period_key):
            skipped_duplicates += 1
            entry = DispatchEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                dispatch_key=dispatch_key,
                hotel_name=hotel_name,
                reporting_period=period_key,
                classification=hotel.classification,
                original_recipient=hotel.record.boss_email,
                actual_recipient=config.get_effective_recipient(hotel.record.boss_email)[0],
                is_redirected=config.get_effective_recipient(hotel.record.boss_email)[1],
                delivery_status="SKIPPED_DUPLICATE",
                generation_method="N/A",
                is_ai_generated=False,
                revenue=hotel.record.revenue,
                orders=hotel.record.orders,
                error_details="Email already dispatched for this reporting period."
            )
            dispatch_results.append(entry)
            continue

        processed_count += 1

        # 4. Content Generation (AI with deterministic fallback)
        summary = generate_summary(hotel, benchmarks, period_label)
        generated_summaries[hotel_name] = summary

        # 5. Dispatch / Preview
        status, actual_recipient, err_msg = dispatcher.dispatch(
            hotel=hotel,
            summary=summary,
            period_key=period_key,
            period_label=period_label
        )

        if status in ("SENT_TO_TEST_INBOX", "SENT_TO_LIVE_PARTNER", "PREVIEW_ONLY"):
            success_count += 1
        else:
            fail_count += 1

        # 6. Audit Logging
        entry = DispatchEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            dispatch_key=dispatch_key,
            hotel_name=hotel_name,
            reporting_period=period_key,
            classification=hotel.classification,
            original_recipient=hotel.record.boss_email,
            actual_recipient=actual_recipient,
            is_redirected=config.get_effective_recipient(hotel.record.boss_email)[1],
            delivery_status=status,
            generation_method=summary.generation_method,
            is_ai_generated=summary.is_ai_generated,
            revenue=hotel.record.revenue,
            orders=hotel.record.orders,
            error_details=err_msg or (summary.error_message or "")
        )
        logger.record_dispatch(entry)
        dispatch_results.append(entry)

    total_raw = len(valid_records) + len(invalid_records)

    return PipelineResult(
        timestamp=run_timestamp,
        reporting_period_key=period_key,
        reporting_period_label=period_label,
        total_raw_records=total_raw,
        valid_records_count=len(valid_records),
        invalid_records_count=len(invalid_records),
        benchmarks=benchmarks,
        processed_count=processed_count,
        skipped_duplicates_count=skipped_duplicates,
        successful_dispatches_count=success_count,
        failed_dispatches_count=fail_count,
        classified_hotels=classified_hotels,
        generated_summaries=generated_summaries,
        dispatch_results=dispatch_results
    )
