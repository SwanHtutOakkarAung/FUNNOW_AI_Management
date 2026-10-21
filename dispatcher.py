"""
Email dispatching module with strict test-recipient isolation, preview mode, and SMTP transport.
"""

import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Tuple
from config import config
from summarizer import GeneratedSummary
from classifier import ClassifiedHotel

def sanitize_filename(name: str) -> str:
    """Replaces unsafe filename characters with underscores."""
    return re.sub(r'[\\/*?:"<>| ]+', '_', name).strip('_')


class EmailDispatcher:
    """Handles dispatching with guaranteed isolation between mock addresses and test inbox."""

    def __init__(self, dry_run: bool = config.DRY_RUN):
        self.dry_run = dry_run

    def dispatch(
        self,
        hotel: ClassifiedHotel,
        summary: GeneratedSummary,
        period_key: str = config.REPORTING_PERIOD_KEY,
        period_label: str = config.REPORTING_PERIOD_LABEL
    ) -> Tuple[str, str, str]:
        """
        Executes delivery based on mode (dry-run preview vs SMTP delivery).
        Returns: (delivery_status, actual_recipient, error_details)
        """
        original_email = hotel.record.boss_email
        actual_recipient, is_redirected = config.get_effective_recipient(original_email)

        # Build full email subject
        if is_redirected:
            effective_subject = f"[TEST MODE | For: {hotel.record.brandname}] {summary.subject}"
        else:
            effective_subject = summary.subject

        # In preview / dry-run mode, we format and write local preview files
        if self.dry_run:
            self._save_local_preview(hotel, summary, effective_subject, actual_recipient, is_redirected, period_key)
            return "PREVIEW_ONLY", actual_recipient, ""

        # Live SMTP delivery mode
        if not config.SMTP_USER or not config.SMTP_PASSWORD:
            err = "SMTP credentials (SMTP_USER / SMTP_PASSWORD) not configured. Cannot perform live transmission."
            self._save_local_preview(hotel, summary, effective_subject, actual_recipient, is_redirected, period_key)
            return "PREVIEW_ONLY", actual_recipient, err

        try:
            self._send_smtp_email(
                recipient=actual_recipient,
                subject=effective_subject,
                body=summary.body,
                original_intended_recipient=original_email,
                is_redirected=is_redirected
            )
            status = "SENT_TO_TEST_INBOX" if is_redirected else "SENT_TO_LIVE_PARTNER"
            return status, actual_recipient, ""
        except Exception as e:
            return "FAILED", actual_recipient, str(e)

    def _save_local_preview(
        self,
        hotel: ClassifiedHotel,
        summary: GeneratedSummary,
        subject: str,
        actual_recipient: str,
        is_redirected: bool,
        period_key: str
    ):
        """Saves formatted text preview into output_previews directory."""
        clean_name = sanitize_filename(hotel.record.brandname)
        out_file = config.OUTPUT_DIR / f"{clean_name}_{period_key}.txt"

        content = (
            f"======================================================================\n"
            f"FUNNOW DISPATCH PREVIEW\n"
            f"Hotel: {hotel.record.brandname}\n"
            f"Classification: {hotel.classification}\n"
            f"Original Recipient in Sheet: {hotel.record.boss_email}\n"
            f"Effective Destination: {actual_recipient} {'(SAFELY REDIRECTED TO TEST)' if is_redirected else '(LIVE)'}\n"
            f"Generation Method: {summary.generation_method} (AI Generated: {summary.is_ai_generated})\n"
            f"Subject: {subject}\n"
            f"======================================================================\n\n"
            f"{summary.body}\n"
        )

        with open(out_file, mode="w", encoding="utf-8") as f:
            f.write(content)

    def _send_smtp_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        original_intended_recipient: str,
        is_redirected: bool
    ):
        """Sends an email via standard SMTP (TLS) with clear attribution headers."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"FUNNOW Automated Operations <{config.SMTP_USER}>"
        msg["To"] = recipient

        # Add custom headers for testing visibility
        if is_redirected:
            msg["X-Original-Intended-Recipient"] = original_intended_recipient
            footer_note = (
                f"\n\n---\n"
                f"[DISPATCH AUDIT NOTE]\n"
                f"This email was safely dispatched in TEST MODE to {recipient}.\n"
                f"The production intended hotel recipient is: {original_intended_recipient}."
            )
            full_body = body + footer_note
        else:
            full_body = body

        msg.attach(MIMEText(full_body, "plain", "utf-8"))

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_USER, [recipient], msg.as_string())
