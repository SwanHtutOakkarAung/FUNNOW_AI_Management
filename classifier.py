"""
Performance classification module using transparent, deterministic business rules.
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from pydantic import BaseModel
from data_loader import HotelRecord


class BenchmarkStats(BaseModel):
    """Calculated benchmarks across all active/positive hotels in the reporting period."""
    sample_size: int
    median_revenue: float
    median_orders: float
    mean_revenue: float
    mean_orders: float
    benchmark_aov: float  # Average Order Value at median level


class ClassifiedHotel(BaseModel):
    """Hotel record enriched with performance metrics and classification tier."""
    record: HotelRecord
    classification: str  # "Doing Well" | "Needs Improvement" | "Data Check"
    aov: float
    revenue_vs_median_pct: float
    orders_vs_median_pct: float
    performance_reasons: List[str]
    coaching_theme: str


def compute_benchmarks(records: List[HotelRecord]) -> BenchmarkStats:
    """
    Computes cohort benchmarks dynamically from live data.
    Critically excludes invalid records and zero-data anomaly records.
    """
    positive_records = [
        r for r in records if r.is_valid and not r.is_zero_data and r.revenue > 0 and r.orders > 0
    ]

    if not positive_records:
        return BenchmarkStats(
            sample_size=0,
            median_revenue=0.0,
            median_orders=0.0,
            mean_revenue=0.0,
            mean_orders=0.0,
            benchmark_aov=0.0,
        )

    revs = [r.revenue for r in positive_records]
    orders = [float(r.orders) for r in positive_records]

    med_rev = float(np.median(revs))
    med_orders = float(np.median(orders))
    mean_rev = float(np.mean(revs))
    mean_orders = float(np.mean(orders))
    bench_aov = round(med_rev / med_orders, 2) if med_orders > 0 else 0.0

    return BenchmarkStats(
        sample_size=len(positive_records),
        median_revenue=med_rev,
        median_orders=med_orders,
        mean_revenue=round(mean_rev, 2),
        mean_orders=round(mean_orders, 2),
        benchmark_aov=bench_aov,
    )


def classify_hotel(record: HotelRecord, benchmarks: BenchmarkStats) -> ClassifiedHotel:
    """
    Classifies a hotel deterministically using the cohort median benchmark:
    - Zero data: 'Data Check' (Flag sync anomaly or closure)
    - Both revenue and orders >= median: 'Doing Well'
    - Either revenue or orders < median: 'Needs Improvement'
    """
    if record.is_zero_data or (record.revenue == 0 and record.orders == 0):
        return ClassifiedHotel(
            record=record,
            classification="Data Check",
            aov=0.0,
            revenue_vs_median_pct=-100.0,
            orders_vs_median_pct=-100.0,
            performance_reasons=[
                "Zero bookings and zero revenue recorded.",
                "Requires partner sync verification: verify whether property was closed for maintenance, had zero bookings, or PMS integration disconnected."
            ],
            coaching_theme="Data Verification & Channel Health"
        )

    aov = round(record.revenue / record.orders, 2) if record.orders > 0 else 0.0

    # Calculate percentage delta relative to cohort median
    rev_delta = 0.0
    if benchmarks.median_revenue > 0:
        rev_delta = round(((record.revenue - benchmarks.median_revenue) / benchmarks.median_revenue) * 100, 1)

    orders_delta = 0.0
    if benchmarks.median_orders > 0:
        orders_delta = round(((record.orders - benchmarks.median_orders) / benchmarks.median_orders) * 100, 1)

    reasons: List[str] = []
    rev_meets = record.revenue >= benchmarks.median_revenue
    orders_meet = record.orders >= benchmarks.median_orders

    if rev_meets and orders_meet:
        classification = "Doing Well"
        reasons.append(f"Revenue meets/exceeds partner median ({'+' if rev_delta >= 0 else ''}{rev_delta}% vs median).")
        reasons.append(f"Booking volume meets/exceeds partner median ({'+' if orders_delta >= 0 else ''}{orders_delta}% vs median).")
        coaching_theme = "Sustained High Demand & Yield Maximization"
    else:
        classification = "Needs Improvement"
        if not rev_meets and not orders_meet:
            reasons.append(f"Revenue is below partner median ({rev_delta}%).")
            reasons.append(f"Booking volume is below partner median ({orders_delta}%).")
            coaching_theme = "Visibility & Conversion Optimization"
        elif rev_meets and not orders_meet:
            reasons.append(f"Revenue is healthy ({'+' if rev_delta >= 0 else ''}{rev_delta}%), but order volume is below median ({orders_delta}%).")
            reasons.append(f"Strong Average Order Value ({aov:,.2f}), opportunity to unlock broader occupancy.")
            coaching_theme = "Volume Growth & Lead-Time Campaigns"
        else:
            reasons.append(f"Order volume is strong ({'+' if orders_delta >= 0 else ''}{orders_delta}%), but revenue is below median ({rev_delta}%).")
            reasons.append(f"Lower Average Order Value ({aov:,.2f}), potential to optimize room pricing or packages.")
            coaching_theme = "Pricing Strategy & Upsell Packaging"

    return ClassifiedHotel(
        record=record,
        classification=classification,
        aov=aov,
        revenue_vs_median_pct=rev_delta,
        orders_vs_median_pct=orders_delta,
        performance_reasons=reasons,
        coaching_theme=coaching_theme
    )


def classify_all_hotels(records: List[HotelRecord]) -> Tuple[List[ClassifiedHotel], BenchmarkStats]:
    """
    Computes cohort benchmarks and classifies all valid hotels.
    """
    benchmarks = compute_benchmarks(records)
    classified = [classify_hotel(r, benchmarks) for r in records if r.is_valid]
    return classified, benchmarks
