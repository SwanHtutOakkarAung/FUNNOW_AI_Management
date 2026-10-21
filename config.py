"""
Configuration and Environment Management for FUNNOW Hotel Performance Automation.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass
class Config:
    # Google Sheet
    GOOGLE_SHEET_ID: str = os.getenv(
        "GOOGLE_SHEET_ID", "18mr5ZyoyYDuuJ0TB4hncKw2CWUxBAjtIupadEoVNz_c"
    )
    GOOGLE_SHEET_TAB_DATA: str = os.getenv("GOOGLE_SHEET_TAB_DATA", "Sheet1")
    GOOGLE_SHEET_TAB_LOG: str = os.getenv("GOOGLE_SHEET_TAB_LOG", "Dispatch Log")

    # Reporting Period assumptions (source sheet does not contain date columns)
    REPORTING_PERIOD_LABEL: str = os.getenv(
        "REPORTING_PERIOD_LABEL",
        "Mon 12 Oct – Sun 18 Oct 2026 (assumed: source sheet has no dates)",
    )
    REPORTING_PERIOD_KEY: str = os.getenv("REPORTING_PERIOD_KEY", "2026-W42")

    # Safe Email Delivery
    TEST_RECIPIENT_EMAIL: str = os.getenv(
        "TEST_RECIPIENT_EMAIL", "amohamonoha@gmail.com"
    )
    ENABLE_LIVE_PARTNER_DELIVERY: bool = (
        os.getenv("ENABLE_LIVE_PARTNER_DELIVERY", "False").strip().lower() == "true"
    )
    DRY_RUN: bool = os.getenv("DRY_RUN", "True").strip().lower() == "true"

    # SMTP Configuration (optional for live test email delivery)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

    # LLM API Keys (optional; deterministic fallback is used if not provided)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Business assumptions
    CURRENCY_SYMBOL: str = os.getenv("CURRENCY_SYMBOL", "NT$")
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Bangkok")

    # Local storage paths
    OUTPUT_DIR: Path = BASE_DIR / "output_previews"
    LOGS_DIR: Path = BASE_DIR / "logs"

    def get_effective_recipient(self, original_email: str) -> tuple[str, bool]:
        """
        Determines the destination email address with strict safety guarantees.
        Returns: (destination_email, is_redirected_to_test)
        """
        if self.ENABLE_LIVE_PARTNER_DELIVERY:
            return original_email.strip(), False
        return self.TEST_RECIPIENT_EMAIL.strip(), True

    @staticmethod
    def get_dispatch_key(hotel_name: str, period_key: str) -> str:
        """
        Generates an idempotent deduplication key for audit tracking.
        Format: brandname_lowercase | period_key_lowercase
        """
        return f"{hotel_name.strip().lower()}|{period_key.strip().lower()}"


# Global default configuration instance
config = Config()

# Ensure local directories exist
config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
