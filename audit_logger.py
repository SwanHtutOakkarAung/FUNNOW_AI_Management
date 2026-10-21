"""
Audit logging and deduplication module to guarantee idempotency and compliance tracking.
"""

import os
import csv
import json
from datetime import datetime, timezone
from typing import List, Set, Optional
from pathlib import Path
from pydantic import BaseModel
from config import config


class DispatchEntry(BaseModel):
    """Immutable audit record representing a dispatch event."""
    timestamp: str
    dispatch_key: str  # hotel_name_clean|reporting_period_key
    hotel_name: str
    reporting_period: str
    classification: str
    original_recipient: str
    actual_recipient: str
    is_redirected: bool
    delivery_status: str  # "PREVIEW_ONLY" | "SENT_TO_TEST_INBOX" | "SKIPPED_DUPLICATE" | "FAILED"
    generation_method: str
    is_ai_generated: bool
    revenue: float
    orders: int
    error_details: str = ""


class AuditLogger:
    """Manages audit persistence to local CSV/JSON and checks for duplicate sends."""

    def __init__(self, log_dir: Path = config.LOGS_DIR):
        self.log_dir = log_dir
        self.csv_path = self.log_dir / "dispatch_log.csv"
        self.jsonl_path = self.log_dir / "dispatch_log.jsonl"
        self._dispatched_keys: Set[str] = set()
        self._load_existing_keys()

    def _load_existing_keys(self):
        """Loads all recorded dispatch keys to ensure idempotency across runs."""
        self._dispatched_keys.clear()
        if self.csv_path.exists():
            with open(self.csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    status = row.get("delivery_status", "")
                    # Only treat as dispatched if actually sent or dry-run confirmed
                    if status in ("SENT_TO_TEST_INBOX", "SENT_TO_LIVE_PARTNER", "PREVIEW_ONLY"):
                        k = row.get("dispatch_key")
                        if k:
                            self._dispatched_keys.add(k.strip().lower())

    def is_dispatched(self, hotel_name: str, period_key: str) -> bool:
        """Checks if an email was already successfully dispatched for this hotel & period."""
        key = config.get_dispatch_key(hotel_name, period_key)
        return key.strip().lower() in self._dispatched_keys

    def record_dispatch(self, entry: DispatchEntry):
        """Persists dispatch entry to local CSV and JSONL audit logs."""
        file_exists = self.csv_path.exists()
        headers = list(entry.model_dump().keys())

        with open(self.csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if not file_exists:
                writer.writeheader()
            writer.writerow(entry.model_dump())

        with open(self.jsonl_path, mode="a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")

        # Update in-memory set
        if entry.delivery_status in ("SENT_TO_TEST_INBOX", "SENT_TO_LIVE_PARTNER", "PREVIEW_ONLY"):
            self._dispatched_keys.add(entry.dispatch_key.strip().lower())

    def get_all_entries(self) -> List[DispatchEntry]:
        """Returns all historical audit entries."""
        if not self.jsonl_path.exists():
            return []
        entries = []
        with open(self.jsonl_path, mode="r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(DispatchEntry.model_validate_json(line))
        return entries
