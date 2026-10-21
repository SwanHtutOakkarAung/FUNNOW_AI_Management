"""
Data ingestion and validation module for Google Sheets hotel performance data.
"""

import io
import re
import urllib.request
import urllib.parse
import pandas as pd
from typing import List, Optional, Tuple
from pydantic import BaseModel, EmailStr, ValidationError, field_validator
from config import config


class HotelRecord(BaseModel):
    """Structured representation of a single hotel's weekly performance."""
    raw_brandname: str
    brandname: str
    revenue: float
    orders: int
    boss_email: str
    is_valid: bool = True
    validation_error: Optional[str] = None
    is_zero_data: bool = False

    @classmethod
    def clean_number(cls, val) -> float:
        """Converts strings with commas, currency symbols, or whitespace to float."""
        if val is None or pd.isna(val):
            raise ValueError("Value is missing / null")
        s = str(val).strip()
        # Remove currency symbols and commas
        cleaned = re.sub(r"[^\d.-]", "", s)
        if not cleaned:
            raise ValueError(f"Cannot parse numeric value from '{val}'")
        return float(cleaned)


def fetch_sheet_csv(sheet_id: str, sheet_name: str) -> pd.DataFrame:
    """
    Fetches a public Google Sheet tab as a pandas DataFrame via gviz endpoint.
    """
    encoded_name = urllib.parse.quote(sheet_name)
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_name}"
    
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "FUNNOW-Automation-Engine/1.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(content))
        return df


def load_and_validate_hotels(
    sheet_id: str = config.GOOGLE_SHEET_ID,
    sheet_name: str = config.GOOGLE_SHEET_TAB_DATA,
    custom_df: Optional[pd.DataFrame] = None
) -> Tuple[List[HotelRecord], List[HotelRecord]]:
    """
    Loads records from Google Sheets (or provided DataFrame) and runs validation.
    Returns: (valid_records, invalid_records)
    """
    if custom_df is not None:
        df = custom_df.copy()
    else:
        df = fetch_sheet_csv(sheet_id, sheet_name)

    # Normalize column names: strip whitespace, handle case
    col_map = {}
    for col in df.columns:
        c_clean = str(col).strip().lower()
        if "brand" in c_clean or "hotel" in c_clean:
            col_map[col] = "brandname"
        elif "revenue" in c_clean:
            col_map[col] = "revenue"
        elif "order" in c_clean:
            col_map[col] = "Order"
        elif "email" in c_clean or "gmail" in c_clean or "boss" in c_clean:
            col_map[col] = "Boss Gmail"

    df = df.rename(columns=col_map)

    valid_records: List[HotelRecord] = []
    invalid_records: List[HotelRecord] = []
    seen_hotels = set()

    for idx, row in df.iterrows():
        raw_name = str(row.get("brandname", "")).strip()
        raw_rev = row.get("revenue")
        raw_orders = row.get("Order")
        raw_email = str(row.get("Boss Gmail", "")).strip()

        # Check for missing brandname
        if not raw_name or raw_name.lower() == "nan":
            invalid_records.append(
                HotelRecord(
                    raw_brandname=raw_name,
                    brandname=f"Row_{idx+1}_Unknown",
                    revenue=0.0,
                    orders=0,
                    boss_email=raw_email,
                    is_valid=False,
                    validation_error="Missing brand name / identifier"
                )
            )
            continue

        # Prevent duplicate hotel names in the same data batch
        norm_name = raw_name.lower()
        if norm_name in seen_hotels:
            invalid_records.append(
                HotelRecord(
                    raw_brandname=raw_name,
                    brandname=raw_name,
                    revenue=0.0,
                    orders=0,
                    boss_email=raw_email,
                    is_valid=False,
                    validation_error="Duplicate hotel entry in batch"
                )
            )
            continue
        seen_hotels.add(norm_name)

        # Validate numbers
        try:
            rev_val = HotelRecord.clean_number(raw_rev)
            if rev_val < 0:
                raise ValueError(f"Negative revenue not allowed: {rev_val}")
        except Exception as e:
            invalid_records.append(
                HotelRecord(
                    raw_brandname=raw_name,
                    brandname=raw_name,
                    revenue=0.0,
                    orders=0,
                    boss_email=raw_email,
                    is_valid=False,
                    validation_error=f"Malformed revenue: {e}"
                )
            )
            continue

        try:
            order_val = int(HotelRecord.clean_number(raw_orders))
            if order_val < 0:
                raise ValueError(f"Negative order count not allowed: {order_val}")
        except Exception as e:
            invalid_records.append(
                HotelRecord(
                    raw_brandname=raw_name,
                    brandname=raw_name,
                    revenue=rev_val,
                    orders=0,
                    boss_email=raw_email,
                    is_valid=False,
                    validation_error=f"Malformed order count: {e}"
                )
            )
            continue

        # Basic email check
        email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(email_regex, raw_email):
            invalid_records.append(
                HotelRecord(
                    raw_brandname=raw_name,
                    brandname=raw_name,
                    revenue=rev_val,
                    orders=order_val,
                    boss_email=raw_email,
                    is_valid=False,
                    validation_error=f"Invalid email address format: '{raw_email}'"
                )
            )
            continue

        # Check for zero-data anomaly
        is_zero = (rev_val == 0.0 and order_val == 0)

        record = HotelRecord(
            raw_brandname=raw_name,
            brandname=raw_name,
            revenue=rev_val,
            orders=order_val,
            boss_email=raw_email,
            is_valid=True,
            is_zero_data=is_zero
        )
        valid_records.append(record)

    return valid_records, invalid_records
