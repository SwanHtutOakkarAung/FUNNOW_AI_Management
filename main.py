"""
CLI entrypoint for running the FUNNOW Hotel Performance Automation Engine.
"""

import argparse
import sys
from config import config
from pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="FUNNOW AI Management Trainee - Automated Hotel Performance Engine"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=config.DRY_RUN,
        help="Generate summaries and save locally without sending live emails (Default: True)"
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Enable live SMTP dispatch to the configured test inbox (amohamonoha@gmail.com)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-dispatch even if hotel was already sent to in this reporting period"
    )
    parser.add_argument(
        "--period-key",
        type=str,
        default=config.REPORTING_PERIOD_KEY,
        help=f"Reporting period key code (default: {config.REPORTING_PERIOD_KEY})"
    )
    parser.add_argument(
        "--period-label",
        type=str,
        default=config.REPORTING_PERIOD_LABEL,
        help="Human-readable reporting period label"
    )

    args = parser.parse_args()

    dry_run_mode = True
    if args.send:
        dry_run_mode = False
    elif not args.dry_run:
        dry_run_mode = False

    print("=" * 75)
    print("🚀 FUNNOW HOTEL PERFORMANCE AUTOMATION ENGINE")
    print("=" * 75)
    print(f"Target Sheet ID:        {config.GOOGLE_SHEET_ID}")
    print(f"Reporting Period:       {args.period_label} [{args.period_key}]")
    print(f"Execution Mode:         {'DRY-RUN / LOCAL PREVIEW' if dry_run_mode else 'LIVE DISPATCH'}")
    print(f"Safe Test Recipient:    {config.TEST_RECIPIENT_EMAIL}")
    print(f"Live Delivery to Mock:  {'ENABLED (Caution!)' if config.ENABLE_LIVE_PARTNER_DELIVERY else 'STRICTLY BLOCKED (Safe)'}")
    print("=" * 75)

    try:
        result = run_pipeline(
            period_key=args.period_key,
            period_label=args.period_label,
            dry_run=dry_run_mode,
            force_resend=args.force
        )

        b = result.benchmarks
        print(f"\n📊 COHORT BENCHMARKS (Computed from {b.sample_size} active hotels):")
        print(f"  • Median Revenue:     {config.CURRENCY_SYMBOL}{b.median_revenue:,.0f}")
        print(f"  • Median Orders:      {b.median_orders:.0f} bookings")
        print(f"  • Benchmark AOV:      {config.CURRENCY_SYMBOL}{b.benchmark_aov:,.2f}")

        print(f"\n🏨 HOTEL PROCESSING & CLASSIFICATION SUMMARY:")
        print(f"{'Hotel Name':<32} {'Rev (' + config.CURRENCY_SYMBOL + ')':<12} {'Orders':<8} {'Classification':<18} {'Delivery Status'}")
        print("-" * 88)

        for hotel in result.classified_hotels:
            name = hotel.record.brandname
            rev_str = f"{hotel.record.revenue:,.0f}"
            orders_str = str(hotel.record.orders)
            cls_str = hotel.classification
            
            # Find dispatch status
            entry = next((e for e in result.dispatch_results if e.hotel_name == name), None)
            stat = entry.delivery_status if entry else "UNKNOWN"
            print(f"{name:<32} {rev_str:<12} {orders_str:<8} {cls_str:<18} {stat}")

        print("\n" + "=" * 75)
        print(f"Batch Execution Completed:")
        print(f"  • Total Hotels Evaluated: {result.total_raw_records}")
        print(f"  • Successfully Dispatched: {result.successful_dispatches_count}")
        print(f"  • Skipped Duplicates:     {result.skipped_duplicates_count}")
        print(f"  • Errors / Failures:      {result.failed_dispatches_count}")
        print(f"  • Audit Log Written To:   {config.LOGS_DIR / 'dispatch_log.csv'}")
        if dry_run_mode:
            print(f"  • Previews Written To:    {config.OUTPUT_DIR}")
        print("=" * 75)

    except Exception as e:
        print(f"\n❌ Pipeline execution encountered an error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
