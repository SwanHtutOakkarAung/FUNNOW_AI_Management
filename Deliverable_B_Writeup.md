# FUNNOW Group — AI Management Trainee Technical Assignment
## Deliverable B: Technical Architecture & Methodology Report

**Candidate:** Isaac Aung (Software Engineering, Mae Fah Luang University)  
**Role Application:** AI Management Trainee  
**Date:** October 2026  
**Repository:** [https://github.com/SwanHtutOakkarAung/FUNNOW_AI_Management](https://github.com/SwanHtutOakkarAung/FUNNOW_AI_Management)  

---

### Executive Summary

Every Monday morning, FUNNOW partner operations teams manually retrieve performance data, assess hotel performance, and write individualized summary emails to hotel owners. This manual routine is repetitive, mentally demanding, and susceptible to human calculation error.

This project delivers a **fully working, automated partner briefing engine** that:
1. Ingests and validates hotel records directly from Google Sheets.
2. Performs deterministic cohort median calculations and classifies properties into `Doing Well`, `Needs Improvement`, and `Data Check`.
3. Isolates zero-data anomaly records (`海角小屋 Cape Cottage`) to prevent misclassifying data feed issues as poor performance.
4. Uses structured prompt engineering with strict anti-hallucination guardrails, backed by a **Deterministic Fallback Engine** that guarantees 100% system reliability without relying on external API uptime.
5. Safely routes all test communications to a dedicated test recipient (`amohamonoha@gmail.com`) with idempotent deduplication and comprehensive audit logging.
6. Provides an interactive Streamlit control dashboard, a CLI entrypoint, and a 10-point automated test suite with 100% passing results.

---

### 1. Problem and Objective

#### The Manual Reporting Problem
Today, FUNNOW employees manually collect weekly hotel performance figures, analyze bookings and revenue against expectations, and draft custom briefing emails for each partner property every Monday morning. 

This manual workflow introduces three core challenges:
* **Repetitive Manual Workload:** Pulling tabular numbers and converting them into written narrative by hand creates operational bottlenecks every Monday.
* **Reporting Inconsistency:** Different account managers apply subjective interpretations of what constitutes "good" vs. "needing improvement," leading to inconsistent messaging across hotel partners.
* **Data Handling Risks:** Manually copying numbers and drafting emails increases the risk of calculation mistakes or accidentally disclosing confidential partner metrics to the wrong recipient.

#### The Automation Objective
The primary objective of this system is to **automate the weekly data-to-communication workflow**:
* Ingest weekly partner data automatically.
* Apply objective, explainable performance classification benchmarks.
* Generate personalized, data-grounded performance briefings.
* Safely dispatch messages to partners while preventing duplicate sends and maintaining a verifiable audit log.

*(Note: In accordance with professional engineering standards, no unsubstantiated percentage time-savings claims are made; the objective is centered on consistency, data integrity, and operational reliability).*

---

### 2. Solution Architecture

The system is architected as a modular, decoupled pipeline. Each stage has a single, testable responsibility:

```
[ Google Sheets Source ] (Sheet1)
           │
           ▼
[ 1. Ingestion & Validation ] (data_loader.py)
   ├── Type casting & numeric sanitization
   ├── RFC-compliant email regex validation
   └── Duplicate batch detection & zero-data anomaly isolation
           │
           ▼
[ 2. Deterministic Performance Analysis ] (classifier.py)
   ├── Dynamic cohort median calculation (Median Rev: NT$315,000 | Median Orders: 71)
   ├── Average Order Value (AOV) calculation
   └── Classification: "Doing Well" | "Needs Improvement" | "Data Check"
           │
           ▼
[ 3. Structured Message Generation ] (summarizer.py)
   ├── Primary: LLM API (Google Gemini / OpenAI) with strict JSON schema
   └── Resilient Fallback: Rule-Based Deterministic Engine (100% uptime guarantee)
           │
           ▼
[ 4. Output Validation & Fallback Audit ] (summarizer.py)
   └── Validates schema, tags generation method ("AI_GENERATED" vs "FALLBACK_DETERMINISTIC")
           │
           ▼
[ 5. Safe Dispatch & Audit Tracker ] (dispatcher.py & audit_logger.py)
   ├── Safety Redirection Proxy (Original Partner -> amohamonoha@gmail.com)
   ├── Dry-Run Preview Storage (output_previews/)
   └── Idempotent Audit Logging (logs/dispatch_log.csv via composite key hotel|period)
           │
           ▼
[ Execution & Monitoring Interfaces ]
   ├── Interactive Web Control Center (app.py via Streamlit)
   ├── Automated Monday Batch CLI (main.py)
   └── Automated Unit & Integration Suite (tests/test_pipeline.py via pytest)
```

#### Operational Execution & Time Zone
* **Operational Time Zone:** Explicitly configured as **`Asia/Bangkok`** (FUNNOW regional operations).
* **Scheduled Monday Execution:** Designed for standard cron trigger (e.g. `0 9 * * 1` for 09:00 AM Bangkok time every Monday).
* **Manual Demonstration Execution:** Fully supported via `python main.py` or the Streamlit web dashboard (`streamlit run app.py`) with dry-run preview toggles.

---

### 3. Technology Selection

Every tool in the stack was selected based on concrete business requirements, reliability, and engineering maintainability:

| Technology | Role in System | Business Requirement & Selection Rationale |
| :--- | :--- | :--- |
| **Python 3.12** | Core Automation Language | **Reliability & Auditability:** Python provides native support for structured typing, robust data manipulation libraries, and deterministic automated unit testing (`pytest`). Unlike visual no-code tools which can become fragile with complex error branching, Python ensures reproducible, version-controlled execution across environments. |
| **Google Sheets API / gviz** | Tabular Data Source | **Operational Usability:** Hotel performance data is managed collaboratively by partner operations teams in Google Sheets. Accessing the sheet via standard endpoints allows automated retrieval without disrupting existing partner management workflows. |
| **Pydantic & pandas** | Data Validation & Calculations | **Defensive Typing:** Pydantic enforces schema contracts at system boundaries. Numeric cleaning regex ensures strings with commas (e.g., `"350,000"`) or currency symbols are safely parsed, while non-numeric or negative values are caught before reaching the AI layer. |
| **Deterministic Code for Math** | Analytical Engine | **Zero Hallucination Guarantee:** LLMs are non-deterministic and notoriously unreliable at mathematical calculations. Cohort medians, ratios, and tier assignments are computed strictly in code to guarantee 100% analytical correctness. |
| **LLMs (Gemini / OpenAI)** | Natural Language Synthesis | **Personalized Tone & Synthesis:** LLMs are used strictly for language synthesis—translating structured business facts into friendly, respectful, and context-adapted partner communications. |
| **Deterministic Template Engine** | Offline & API Fail-Safe | **Operational Resilience:** External AI APIs can experience rate limits, quota exhaustion, or network timeouts. The deterministic fallback engine ensures partner briefings are always generated on schedule without stalling Monday operations. |
| **SMTP with Safe Redirection** | Communication Transport | **Safe Delivery:** Uses standard SMTP over TLS (port 587) with an immutable safety proxy that intercepts all partner emails and redirects them to the tester (`amohamonoha@gmail.com`). |
| **CSV & JSONL Logging** | Audit & Idempotency Store | **Compliance & Deduplication:** Logging records delivery provider acceptance, generation methods, timestamps, and composite keys (`hotel|week`) to prevent accidental duplicate weekly transmissions. |

---

### 4. Data Processing and Performance Classification

#### Source Data Inspection
The provided dataset contains 10 hotel rows with four fields: `brandname`, `revenue`, `Order`, `Boss Gmail`.

**Critical Analytical Observation:**
The mock dataset contains a single-week snapshot without:
* Explicit revenue or booking targets.
* Historical comparisons (no previous week data).
* Dated transaction logs.

Therefore, we must use a **transparent demonstration assumption** rather than inventing fictitious targets or historical trends.

#### Benchmark Calculation
To establish an objective benchmark, the system dynamically calculates the **Cohort Median** across all valid, nonzero properties:
* **Median Revenue:** **NT$315,000**
* **Median Orders:** **71 bookings**
* **Benchmark AOV (Average Order Value):** **NT$4,436.62**

*Why Median instead of Mean?* In hospitality datasets, revenue is heavily skewed by premium boutique properties. In our cohort, revenue ranges from NT$92,000 to NT$598,000. The median provides a robust central benchmark that is not distorted by extreme outliers.

#### Three-Tier Classification Rules
```
                    ┌────────────────────────┐
                    │ Raw Hotel Performance  │
                    └───────────┬────────────┘
                                │
                 Is Revenue == 0 & Orders == 0?
                                │
                 ├── Yes ───────┴──────── No ──┐
                 ▼                             ▼
        ┌──────────────────┐      Revenue >= Median & Orders >= Median?
        │    Data Check    │                   │
        │ (Anomaly Review) │     ├── Yes ──────┴──────── No ──┐
        └──────────────────┘     ▼                             ▼
                        ┌──────────────────┐          ┌──────────────────┐
                        │    Doing Well    │          │Needs Improvement │
                        │  (High Yield)    │          │  (Optimization)  │
                        └──────────────────┘          └──────────────────┘
```

1. **`Data Check` (Zero-Data / Anomaly Review):**
   * *Rule:* Revenue == 0 and Orders == 0 (`海角小屋 Cape Cottage`).
   * *Business Justification:* Treating zero data as "poor performance" damages partner trust. Zero bookings often reflect temporary property closure, seasonal maintenance, or a broken PMS channel integration. The system flags this for partner operations verification.
2. **`Doing Well` (Balanced High Performers):**
   * *Rule:* Revenue $\ge$ Median Revenue (NT$315k) **AND** Orders $\ge$ Median Orders (71).
   * *Hotels:* `河畔城市旅店 Riverside Hotel` (exact median benchmark), `星辰商務旅店 Starlight Biz`, `望海精品旅館 Ocean View`, `松河商旅 Songhe Inn`, `晴空溫泉會館 Sky Spa Resort`.
3. **`Needs Improvement` (Underperforming in Revenue or Orders):**
   * *Rule:* Revenue $<$ Median Revenue **OR** Orders $<$ Median Orders.
   * *Hotels:* `森丘山居 Forest Hill`, `藍灣青年旅舍 Blue Bay Hostel`, `文青行旅 Artis Inn`, `橙光設計旅店 Orange Light`.
   * *Sub-logic:* Differentiates between properties with strong AOV but low volume (suggesting lead-time / off-peak campaigns) versus high volume but low revenue (suggesting room pricing or upsell packaging).

*Important Limitation Note:* These thresholds are demonstration assumptions. In production, classification would incorporate property capacity (room count), location tier, and historical seasonality rather than a single pooled cohort median.

---

### 5. AI Message Generation

The core philosophy of the communication engine is **strict separation of numerical analysis from natural-language generation**.

#### Structured Information Passing
The AI never calculates metrics. It receives a pre-validated, verified JSON payload:
```json
{
  "hotel_name": "森丘山居 Forest Hill",
  "reporting_period": "Mon 12 Oct – Sun 18 Oct 2026 (assumed: source sheet has no dates)",
  "revenue": 92000.0,
  "revenue_formatted": "NT$92,000",
  "orders": 21,
  "aov_formatted": "NT$4,381",
  "cohort_median_revenue": "NT$315,000",
  "cohort_median_orders": 71.0,
  "classification": "Needs Improvement",
  "performance_reasons": [
    "Revenue is below partner median (-70.8%).",
    "Booking volume is below partner median (-70.4%)."
  ],
  "coaching_theme": "Visibility & Conversion Optimization"
}
```

#### Factual Guardrails & Prompt Instructions
The system instruction enforces seven strict behavioral guardrails:
1. **Grounding Constraint:** Reference *only* the facts and figures provided in the JSON payload.
2. **Anti-Hallucination Rule:** Never invent previous week comparisons, historical trends, or occupancy rates.
3. **Target Guardrail:** Never claim knowledge of internal hotel business goals.
4. **Partner Privacy Guardrail:** Never reveal identifiable metrics or names of competing hotels; refer only to aggregate cohort medians.
5. **Tone Adaptation:** Maintain a respectful, supportive, and professional tone.
6. **Constructive Coaching:** Provide appropriately qualified, practical suggestions based on the assigned coaching theme.
7. **Structured Output:** Respond exclusively in valid JSON with `subject` and `body` fields.

#### Output Validation & Deterministic Fallback Engine
Before any message is queued:
1. The response is parsed and validated against the expected schema (`subject`, `body`).
2. If the LLM API fails (e.g., quota exceeded, network disconnect, or missing API key), the system immediately engages the **Deterministic Fallback Engine**.
3. The fallback engine generates a tailored, professional briefing using deterministic business templates.
4. The audit log explicitly records `generation_method: "FALLBACK_DETERMINISTIC"` and `is_ai_generated: false`—ensuring full transparency.

---

### 6. Workflow Automation and Email Delivery

#### Safe Email Delivery Architecture
During testing, sending unvetted automated emails to real partner addresses is unacceptable. The system implements a three-layer safety proxy:
* **Default Dry-Run Mode:** `DRY_RUN=True` writes full email previews to `output_previews/` without making network connections.
* **Redirection Proxy:** Even when live sending is enabled, `ENABLE_LIVE_PARTNER_DELIVERY` defaults to `False`. All messages are redirected to the configured test recipient (`amohamonoha@gmail.com`).
* **Header Attribution:** Test emails include headers (`X-Original-Intended-Recipient`) and subject prefixes showing the original intended recipient.

#### Duplicate Execution Prevention (Idempotency)
To protect partners from receiving duplicate emails if an automated batch is re-run on Monday:
* A normalized composite key is generated: `clean(brandname)|clean(reporting_period_key)` (e.g. `forest hill|2026-w42`).
* Before dispatch, `audit_logger.py` checks `logs/dispatch_log.csv`. If a successful send or preview already exists for that period, the hotel is skipped (`SKIPPED_DUPLICATE`) unless `--force` is explicitly specified.

#### Logging & Failure Tracking
The audit logger records:
* `timestamp` (ISO-8601 with timezone)
* `dispatch_key`
* `hotel_name`
* `classification`
* `original_recipient` vs. `actual_recipient`
* `delivery_status` (`SENT_TO_TEST_INBOX`, `PREVIEW_ONLY`, `SKIPPED_DUPLICATE`, `FAILED`)
* `generation_method` and `is_ai_generated`
* `error_details`

*Delivery Provider Acceptance vs. Inbox Delivery:* The system marks status as sent only after the SMTP server accepts the message payload, distinguishing transport acceptance from guaranteed inbox delivery.

---

### 7. Testing and Results

#### Automated Test Suite Outcomes (`pytest`)
A dedicated automated test suite in `tests/test_pipeline.py` verifies all 10 evaluation scenarios:

| # | Test Scenario | Verified Behavior | Result |
| :-: | :--- | :--- | :-: |
| **1** | Valid Hotel Record Processing | Ingests clean records, parses numeric values and emails. | **PASSED** |
| **2** | Correct Performance Classification | Verifies median computation and Doing Well / Needs Improvement tiers. | **PASSED** |
| **3** | Personalized Summaries | Confirms distinct messaging generated for different performance tiers. | **PASSED** |
| **4** | Zero Revenue and Zero Orders | Confirms `Data Check` classification and PMS sync verification text. | **PASSED** |
| **5** | Missing or Invalid Data | Rejects corrupt revenue, negative counts, and blank names. | **PASSED** |
| **6** | Invalid Email Addresses | Rejects malformed email formats before dispatch. | **PASSED** |
| **7** | LLM API Failure Fallback | Confirms seamless fallback to deterministic template when API fails. | **PASSED** |
| **8** | Email Delivery Failure | Catches SMTP transport exceptions and logs `FAILED` with error text. | **PASSED** |
| **9** | Duplicate Workflow Execution | Skips already-dispatched hotels on subsequent runs. | **PASSED** |
| **10** | Safe Test Inbox Redirection | Enforces routing of all emails to `amohamonoha@gmail.com`. | **PASSED** |

#### Sample Generated Email Outputs

##### Example 1: Doing Well Property (`晴空溫泉會館 Sky Spa Resort`)
> **Subject:** `[TEST MODE | For: 晴空溫泉會館 Sky Spa Resort] FUNNOW Weekly Partner Briefing: Strong Performance — 晴空溫泉會館 Sky Spa Resort`  
> **Destination:** `amohamonoha@gmail.com` (Intended: `boss.skyspa@example.com`)  
> **Body:**  
> Dear 晴空溫泉會館 Sky Spa Resort Management Team,  
>  
> We are pleased to share your performance briefing for Mon 12 Oct – Sun 18 Oct 2026.  
>  
> **Key Performance Highlights:**  
> • Total Revenue: NT$598,000 (Cohort Median: NT$315,000)  
> • Confirmed Bookings: 102 orders (Cohort Median: 71)  
> • Average Order Value: NT$5,863  
>  
> **Analysis & Observations:**  
> Your property performed strongly this week, meeting or exceeding cohort benchmarks in both revenue and booking volume. Your Average Order Value reflects solid guest spending and steady demand.  
>  
> **Strategic Recommendations:**  
> • Maintain current inventory availability to capture high-intent travelers.  
> • Review weekend vs. weekday availability to further maximize peak-time room rates.  
>  
> Warm regards,  
> FUNNOW Partner Growth Team

---

##### Example 2: Needs Improvement Property (`森丘山居 Forest Hill`)
> **Subject:** `[TEST MODE | For: 森丘山居 Forest Hill] FUNNOW Weekly Partner Briefing: Optimization Opportunities — 森丘山居 Forest Hill`  
> **Destination:** `amohamonoha@gmail.com` (Intended: `owner.foresthill@example.com`)  
> **Body:**  
> Dear 森丘山居 Forest Hill Management Team,  
>  
> Here is your weekly performance summary for Mon 12 Oct – Sun 18 Oct 2026.  
>  
> **Weekly Performance Overview:**  
> • Total Revenue: NT$92,000 (Cohort Median: NT$315,000)  
> • Confirmed Bookings: 21 orders (Cohort Median: 71)  
> • Average Order Value: NT$4,381  
>  
> **Analysis & Action Plan:**  
> This week's revenue (NT$92,000) and booking volume (21) both landed below the cohort medians (NT$315,000 and 71 orders). We recommend reviewing your listing photos, checking competitive rate parity on FUNNOW, and opening up last-minute flash availability to stimulate conversion.  
>  
> Our account management team is available if you would like support setting up promotional campaigns.  
>  
> Warm regards,  
> FUNNOW Partner Growth Team

---

##### Example 3: Data Check Anomaly Property (`海角小屋 Cape Cottage`)
> **Subject:** `[TEST MODE | For: 海角小屋 Cape Cottage] [Action Required] FUNNOW Weekly Data Sync Check — 海角小屋 Cape Cottage`  
> **Destination:** `amohamonoha@gmail.com` (Intended: `owner.capecottage@example.com`)  
> **Body:**  
> Dear 海角小屋 Cape Cottage Partner Team,  
>  
> During our automated weekly performance sync for the period Mon 12 Oct – Sun 18 Oct 2026, FUNNOW recorded NT$0 in revenue and 0 bookings for your property.  
>  
> Before our team compiles your weekly yield analysis, please verify whether:  
> 1. The property was temporarily closed or under scheduled maintenance.  
> 2. There were genuinely no completed stays during this calendar week.  
> 3. Your PMS / channel manager integration experienced a sync interruption.  
>  
> Please reply to this email to confirm your property status so we can update your dashboard accurately.  
>  
> Best regards,  
> FUNNOW Partner Operations Team

---

### 8. Limitations and Future Improvements

1. **Absence of Dates and Historical Baseline in Source:**
   * *Limitation:* The mock Google Sheet is an undated single-week snapshot. Without historical tables, true week-over-week trends cannot be computed without risking hallucination.
   * *Production Improvement:* Integrate with FUNNOW's transactional database (e.g., PostgreSQL or Google BigQuery) partitioned by calendar week to automatically compute true WoW, MoM, and YoY growth rates.
2. **Cohort Homogeneity vs. Segmented Benchmarking:**
   * *Limitation:* Benchmarks currently treat luxury resorts, business hotels, and budget hostels within a single pooled cohort.
   * *Production Improvement:* Segment properties by category (e.g., Hot Spring Resort, Urban Business, Boutique Hostel) and geographic region (e.g., Taipei, Taichung, Bangkok) to provide fairer, category-specific peer medians.
3. **Channel Delivery & Engagement Feedback Loop:**
   * *Limitation:* SMTP tracking confirms delivery-provider acceptance, but cannot verify whether the partner opened the email.
   * *Production Improvement:* Implement SendGrid or Amazon SES webhook events to track email opens, click-through rates, and bounce rates directly in the dispatch log.
4. **Multi-Channel Dispatch:**
   * *Production Improvement:* In Asian markets like Taiwan and Thailand, hotel managers frequently communicate via LINE Official Accounts or WhatsApp Business. Future iterations can add messaging API dispatch alongside email.

---

### Conclusion

This automation solution demonstrates that AI in business operations is most effective when paired with **defensive software engineering**:
* Deterministic code handles data cleaning and mathematical benchmarking.
* Prompt engineering with strict guardrails ensures factual, safe natural language synthesis.
* Built-in fallback engines and safety proxies protect partner relationships and guarantee 100% operational uptime.

The system is fully reproducible, comprehensively tested, and ready for deployment.
