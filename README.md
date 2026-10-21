# 🏨 FUNNOW Hotel Performance Automation Engine

An end-to-end, automated partner operations and decision-support pipeline built for the **FUNNOW Group AI Management Trainee Assignment**.

This system automates the Monday morning weekly performance evaluation for hotel partners. It fetches live data from Google Sheets, deterministically benchmarks cohort metrics, classifies properties, generates personalized data-grounded briefings with factual safeguards, and safely dispatches emails with duplicate-send prevention and audit logging.

---

## 🌟 Key Features

1. **Deterministic Cohort Benchmarking:**
   * Dynamically calculates median revenue, median bookings, and Average Order Value (AOV) from the live active cohort.
   * Isolates and flags zero-data anomalies (`Data Check`) without falsely treating them as poor performance.
2. **Responsible AI Generation with Guaranteed Fallback:**
   * Prompts LLMs (Gemini / OpenAI) under strict factual guardrails (zero hallucination of unsupplied dates, trends, or comparative percentages).
   * Transparent, built-in **Deterministic Fallback Engine** that guarantees 100% system uptime even if LLM APIs or credentials are unavailable.
3. **Ironclad Email Safety & Redirection:**
   * **Never contacts mock partners during testing.** All messages are redirected to the configured test inbox (`amohamonoha@gmail.com`).
   * Dry-Run Preview mode enabled by default (writes full previews to `output_previews/`).
4. **Idempotent Audit Logging:**
   * Generates composite deduplication keys (`hotel_name|reporting_period`) to prevent accidental duplicate weekly transmissions.
5. **Interactive Streamlit Control Center & Full Test Suite:**
   * One-click batch trigger and real-time visual inspection UI.
   * Comprehensive `pytest` suite validating all 10 edge cases and business requirements.

---

## 📁 Repository Structure

```
FUNNOW_AI_Management/
├── app.py                     # Streamlit web dashboard for interactive review & batch runs
├── main.py                    # Production CLI entrypoint (--dry-run, --send, --force)
├── pipeline.py                # End-to-end workflow orchestrator
├── config.py                  # Environment config, test email routing, composite keys
├── data_loader.py             # Google Sheet fetcher, type conversion, and Pydantic validation
├── classifier.py              # Cohort medians and deterministic classification logic
├── summarizer.py              # LLM integration (Gemini/OpenAI) + deterministic fallback engine
├── dispatcher.py              # Safe email transport with test redirection and dry-run storage
├── audit_logger.py            # Idempotent CSV/JSON dispatch audit logger
├── requirements.txt           # Project dependencies
├── pytest.ini                 # Pytest configuration
├── Deliverable_B_Writeup.md   # Official technical submission write-up
├── output_previews/           # Generated email previews (saved during dry runs)
├── logs/                      # Audit dispatch logs (dispatch_log.csv & dispatch_log.jsonl)
└── tests/
    ├── __init__.py
    └── test_pipeline.py       # 10 automated unit & integration tests
```

---

## 🚀 Quick Start (Under 2 Minutes)

### 1. Environment Setup

```bash
# 1. Clone repository and navigate to folder
cd FUNNOW_AI_Management

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### 2. Configuration (`.env`)

The project comes pre-configured with safe defaults in `.env`:
```ini
# Safe test recipient (All outgoing emails route here during testing)
TEST_RECIPIENT_EMAIL=amohamonoha@gmail.com
ENABLE_LIVE_PARTNER_DELIVERY=False
DRY_RUN=True

# Default reporting period label (assumed since Google Sheet has no date column)
REPORTING_PERIOD_LABEL="Mon 12 Oct – Sun 18 Oct 2026 (assumed: source sheet has no dates)"
REPORTING_PERIOD_KEY="2026-W42"
```

---

## 💻 Running the Automation

### Option A: Run via CLI (Default: Dry Run / Local Preview)

```bash
# Run weekly batch with safe local previews
python main.py

# Force re-dispatch (bypassing duplicate check)
python main.py --force

# Live test email dispatch (routes only to amohamonoha@gmail.com via SMTP)
python main.py --send
```

### Option B: Interactive Streamlit Web Control Center

Launch the web dashboard to visually inspect cohort statistics, preview individual email drafts, and trigger batches:

```bash
streamlit run app.py
```

---

## 🧪 Automated Testing

Run the test suite covering all 10 technical requirements:

```bash
pytest -v
```

**Test Coverage Summary:**
1. `test_valid_hotel_record_processing` - Parses and validates clean records.
2. `test_correct_performance_classification` - Verifies median calculations and tier logic.
3. `test_personalized_summaries` - Validates customized messaging for different performance tiers.
4. `test_zero_revenue_and_zero_orders` - Verifies special "Data Check" anomaly flagging.
5. `test_invalid_or_missing_fields` - Rejects corrupt revenue, negative counts, or missing brand names.
6. `test_invalid_email_addresses` - Catches malformed email addresses.
7. `test_llm_api_failure_fallback` - Confirms automatic activation of deterministic fallback when LLM fails.
8. `test_email_delivery_failure` - Captures and logs SMTP transport failures.
9. `test_duplicate_execution_prevention` - Ensures same `hotel|period` key is skipped on subsequent runs.
10. `test_safe_redirection_to_test_inbox` - Enforces destination redirection to `amohamonoha@gmail.com`.

---

## 📄 Deliverable Documentation

For the detailed submission report explaining the architectural rationale, threshold methodology, and prompt safety design, see [Deliverable_B_Writeup.md](Deliverable_B_Writeup.md).
