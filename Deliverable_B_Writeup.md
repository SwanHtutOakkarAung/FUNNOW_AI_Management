# FUNNOW Group — AI Management Trainee Technical Assignment
## Deliverable B: Technical Architecture & Methodology Report

**Candidate:** Isaac Aung (Software Engineering, Mae Fah Luang University)  
**Role Application:** AI Management Trainee  
**Date:** October 2026  
**Repository:** `FUNNOW_AI_Management`  

---

### Executive Summary

Every Monday morning, FUNNOW account managers manually pull hotel performance data, analyze week-over-week revenue and booking metrics, write personalized emails, and send them to hotel partners. This manual process is time-consuming, repetitive, and vulnerable to human calculation errors.

This project delivers a **production-grade, automated decision-support and communication engine** that:
1. Dynamically ingests partner data from Google Sheets.
2. Applies deterministic, explainable classification rules based on cohort medians.
3. Isolates data sync anomalies (zero revenue / zero orders) into an actionable `Data Check` category.
4. Leverages LLMs (Google Gemini / OpenAI) with strict factual guardrails and an automatic, offline-resilient **Deterministic Fallback Engine**.
5. Dispatches personalized briefings with guaranteed email isolation (redirecting all messages to a safe test inbox) and idempotent audit logging.
6. Provides an interactive Streamlit control dashboard and a 100% automated `pytest` test suite.

---

### 1. Problem and Objective

| Business Problem | Operational Impact | Automated Solution |
| :--- | :--- | :--- |
| **Manual Data Extraction** | Employees spend hours retrieving and collating spreadsheets every Monday morning. | Automated API/CSV ingestion that cleans and parses partner records in under 2 seconds. |
| **Subjective Performance Evaluation** | Different account managers apply arbitrary definitions of "good" vs "bad" performance. | Objective, dynamic cohort median benchmarking (`Doing Well`, `Needs Improvement`, `Data Check`). |
| **Repetitive Writing & Error Risk** | High cognitive load in drafting 10+ personalized emails leads to copy-paste mistakes and data leaks. | AI-driven briefing generator with structured inputs and deterministic fallback templates. |
| **Partner Communication Safety** | Risk of sending unvetted test messages to real partner contacts. | Strict safety proxy routing all communications to `amohamonoha@gmail.com` with full audit logs. |

---

### 2. Architecture Overview

The system is structured as a modular, decoupled pipeline following clean software engineering principles:

```
[ Google Sheets (Sheet1) ]
           │
           ▼
[ Data Ingestion & Validation ] (data_loader.py)
   ├── Type casting & cleaning
   ├── Email regex validation
   └── Deduplication & anomaly check
           │
           ▼
[ Dynamic Benchmarking & Classification ] (classifier.py)
   ├── Computes cohort median revenue & orders (excluding anomalies)
   ├── Calculates Average Order Value (AOV)
   └── Assigns: "Doing Well" | "Needs Improvement" | "Data Check"
           │
           ▼
[ Summary Generation Engine ] (summarizer.py)
   ├── Primary: LLM API (Gemini / OpenAI) with strict JSON schema
   └── Fail-safe: Deterministic Rule-Based Fallback Engine (100% uptime)
           │
           ▼
[ Safe Dispatch & Audit Tracker ] (dispatcher.py & audit_logger.py)
   ├── Redirection Proxy (Original Email -> amohamonoha@gmail.com)
   ├── Dry-Run Preview Storage (output_previews/)
   └── Idempotent Audit Logging (logs/dispatch_log.csv via hotel|week key)
           │
           ▼
[ User Interface & Execution Layers ]
   ├── CLI Entrypoint (main.py)
   ├── Web Control Center (app.py via Streamlit)
   └── Automated Test Suite (tests/test_pipeline.py via pytest)
```

---

### 3. Technology-Selection Rationale

The FUNNOW assignment explicitly allows any tool or programming language. A comparison was conducted between a no-code tool (such as **n8n**) and a **code-first Python architecture**:

| Evaluation Factor | No-Code (n8n Workflow) | Code-First Python Pipeline (Chosen Solution) | Rationale |
| :--- | :--- | :--- | :--- |
| **Reliability & Idempotency** | Requires complex multi-node branching to handle retries and deduplication. | Implemented cleanly via composite keys (`hotel\|period`) and file/database persistence. | **Python Wins**: Critical business operations require transparent, deterministic control over edge cases. |
| **Error Handling & Fallback** | API quota or token limits often halt workflows without extensive try-catch nodes. | Transparent exception handling that seamlessly shifts to a deterministic template fallback. | **Python Wins**: Zero downtime; partners always receive accurate briefings even during API outages. |
| **Automated Testing** | Difficult to unit-test individual logic nodes or mock external APIs. | Integrated `pytest` test suite executing 10 automated test scenarios in 0.7 seconds. | **Python Wins**: High testability is standard for software engineering assessments. |
| **Setup & Reproducibility** | Requires running an n8n server, configuring webhooks, and manually importing UI JSON. | Simple `pip install -r requirements.txt` and `python main.py`. Zero environment friction. | **Python Wins**: Evaluators can run and verify the codebase immediately. |
| **Interactivity** | Limited to n8n canvas. | Lightweight Streamlit web app (`app.py`) for visual inspection, one-click execution, and CSV downloads. | **Python Wins**: Combines engineering depth with an intuitive user interface. |

---

### 4. Data Preparation and Validation

The live dataset contains 10 hotel rows (`brandname`, `revenue`, `Order`, `Boss Gmail`). Data preparation in `data_loader.py` enforces the following rules:

1. **Numeric Sanitization:** Revenue values with commas, currency signs, or whitespace (e.g. `"350,000"`) are sanitized using regex and validated against negative values.
2. **Identity & Email Validation:** Hotel brand names are checked for non-empty strings. Email addresses are validated against standard RFC-compliant regex patterns.
3. **Duplicate Batch Prevention:** If the same hotel name appears twice in a single sheet ingestion, subsequent entries are rejected to prevent double-processing.
4. **Data Isolation (Zero-Data Anomaly):** Records where both revenue and order counts are zero (`海角小屋 Cape Cottage`) are isolated as `is_zero_data=True` and excluded from cohort median calculations to prevent skewing the baseline.

---

### 5. Classification Threshold Methodology

#### The Baseline Metric: Median vs. Mean
In hotel performance datasets, revenue distributions are frequently skewed by high-volume luxury resorts or boutique properties. 
* In this cohort, `晴空溫泉會館 Sky Spa Resort` generated **NT$598,000** while `森丘山居 Forest Hill` generated **NT$92,000**.
* Because arithmetic mean is heavily distorted by extreme outliers, the **Cohort Median** was selected as the robust central tendency indicator.

#### Cohort Benchmarks (Calculated dynamically from live active hotels):
* **Median Revenue:** **NT$315,000**
* **Median Order Count:** **71 orders**
* **Benchmark AOV (Average Order Value):** **NT$4,436.62**

#### Three-Tier Classification Logic:
1. **`Data Check` (Zero-Data / Anomaly):**
   * *Condition:* `Revenue == 0` AND `Orders == 0`.
   * *Business Justification:* Treating zero data as "poor performance" harms partner relationships. It typically indicates a PMS disconnect, seasonal closure, or maintenance downtime. The system flags this for partner operations verification.
2. **`Doing Well` (Balanced High Performers):**
   * *Condition:* `Revenue >= Median Revenue` AND `Orders >= Median Orders`.
   * *Cohort Members:* `河畔城市旅店 Riverside Hotel` (exact median benchmark), `星辰商務旅店 Starlight Biz`, `望海精品旅館 Ocean View`, `松河商旅 Songhe Inn`, `晴空溫泉會館 Sky Spa Resort`.
   * *Coaching Focus:* Yield optimization, rate packaging, and locking in advance demand.
3. **`Needs Improvement` (Underperforming in Volume or Revenue):**
   * *Condition:* `Revenue < Median Revenue` OR `Orders < Median Orders`.
   * *Cohort Members:* `森丘山居 Forest Hill`, `藍灣青年旅舍 Blue Bay Hostel`, `文青行旅 Artis Inn`, `橙光設計旅店 Orange Light`.
   * *Granular Sub-Logic:*
     * If volume is high but revenue is low $\rightarrow$ Focus on upselling room tiers and adjusting base ADR.
     * If revenue is healthy but volume is low $\rightarrow$ High AOV property; focus on off-peak promotions and lead-time campaigns.
     * If both are low $\rightarrow$ Review listing photos, rate parity, and promotional participation.

---

### 6. AI Prompt Design and Factual Safeguards

Language models can hallucinate trends, growth percentages, or historical comparisons when analyzing tabular data. The prompt architecture in `summarizer.py` enforces three core safeguards:

#### Prompt Guardrail Architecture:
```
┌────────────────────────────────────────────────────────┐
│                   SYSTEM INSTRUCTION                   │
│ - Act as FUNNOW Partner Operations Assistant.          │
│ - Strict Grounding: ONLY use facts in provided JSON.   │
│ - Negative Constraint: NEVER invent historical trends, │
│   WoW growth %, or unsupplied occupancy numbers.       │
│ - Privacy: NEVER disclose other partner names or data. │
│ - Output Format: Valid JSON {"subject": "", "body": ""}│
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                   STRUCTURED CONTEXT                   │
│ - Hotel Name: "森丘山居 Forest Hill"                   │
│ - Revenue: NT$92,000 (Median: NT$315,000)              │
│ - Orders: 21 (Median: 71)                              │
│ - AOV: NT$4,381 (Median: NT$4,437)                     │
│ - Classification: "Needs Improvement"                  │
│ - Specific Coaching Theme: "Visibility & Conversion"   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                RESPONSE VALIDATION & PARSING           │
│ Validates JSON schema -> Extracts Subject & Body       │
└────────────────────────────────────────────────────────┘
```

#### Deterministic Fallback Engine
If an LLM API call fails (network timeout, rate limiting, or absent API keys), the system immediately engages `generate_fallback_summary()`.
* **Zero Downtime:** Every hotel receives a fully formatted, professional briefing.
* **Audit Transparency:** Fallback emails are clearly tagged with `generation_method: "FALLBACK_DETERMINISTIC"` and `is_ai_generated: false` in the dispatch log.

---

### 7. Email Automation & Safety Guarantees

#### Test Recipient Redirection Proxy
During evaluation and development, accidentally emailing real hotel owners is catastrophic. `config.py` and `dispatcher.py` implement an immutable safety proxy:
* `ENABLE_LIVE_PARTNER_DELIVERY` defaults to `False`.
* When `False`, **100% of generated emails are redirected to `amohamonoha@gmail.com`**.
* The email subject and header clearly display:
  `[TEST MODE | For: 森丘山居 Forest Hill] FUNNOW Weekly Partner Briefing...`
  along with `X-Original-Intended-Recipient: owner.foresthill@example.com`.

#### Dry-Run Mode
By default, the engine runs in `DRY_RUN=True` mode, rendering formatted briefings directly into `output_previews/` and logging `PREVIEW_ONLY` without triggering external network traffic.

#### Idempotency & Deduplication
To prevent sending duplicate weekly emails to partners if an automation script runs multiple times on Monday:
* A composite key is constructed: `clean(brandname)|clean(reporting_period_key)` (e.g. `forest hill|2026-w42`).
* If this key exists with a successful status in `logs/dispatch_log.csv`, subsequent executions mark the record as `SKIPPED_DUPLICATE` and bypass dispatching unless `--force` is explicitly provided.

---

### 8. Testing, Limitations, and Future Improvements

#### Automated Test Verification (`pytest`)
All 10 assignment test scenarios are automated in `tests/test_pipeline.py`:
1. `test_valid_hotel_record_processing` — **PASSED**
2. `test_correct_performance_classification` — **PASSED**
3. `test_personalized_summaries` — **PASSED**
4. `test_zero_revenue_and_zero_orders` — **PASSED**
5. `test_invalid_or_missing_fields` — **PASSED**
6. `test_invalid_email_addresses` — **PASSED**
7. `test_llm_api_failure_fallback` — **PASSED**
8. `test_email_delivery_failure` — **PASSED**
9. `test_duplicate_execution_prevention` — **PASSED**
10. `test_safe_redirection_to_test_inbox` — **PASSED**

#### Current Limitations & Production Roadmap
1. **Absence of Date / Historical Data in Source:**
   * *Limitation:* The mock Google Sheet lacks a timestamp column or prior-week records.
   * *Production Improvement:* Ingest from FUNNOW's data warehouse (BigQuery / PostgreSQL) with partitioned weekly tables to calculate true Week-over-Week (WoW) and Year-over-Year (YoY) delta metrics.
2. **Fixed Benchmark vs. Segmented Benchmark:**
   * *Limitation:* All 10 hotels are benchmarked as a single cohort.
   * *Production Improvement:* Segment benchmarks by property type (e.g., Hostels vs. Luxury Hot Spring Resorts) and geographic region (Taipei, Taichung, Bangkok) for fairer comparisons.
3. **Dispatch Feedback Loop:**
   * *Limitation:* The current system confirms SMTP server acceptance (`SENT_TO_TEST_INBOX`), but not inbox opens or click-throughs.
   * *Production Improvement:* Integrate SendGrid or AWS SES webhooks to record open rates, bounces, and partner replies directly back into the CRM.

---

### Conclusion

This solution fulfills all technical and business requirements of the FUNNOW AI Management Trainee assignment. It combines strict software engineering discipline, resilient AI prompt engineering, and an intuitive user interface, demonstrating ready-to-deploy value for FUNNOW partner operations.
