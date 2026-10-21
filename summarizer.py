"""
Summary generation module featuring LLM integration (Gemini & OpenAI)
and a robust deterministic fallback engine with strict factual safeguards.
"""

import os
import json
import logging
from typing import Optional
from pydantic import BaseModel
from config import config
from classifier import ClassifiedHotel, BenchmarkStats

logger = logging.getLogger(__name__)


class GeneratedSummary(BaseModel):
    """The generated email message with audit metadata."""
    subject: str
    body: str
    is_ai_generated: bool
    generation_method: str  # "GEMINI_API" | "OPENAI_API" | "FALLBACK_DETERMINISTIC"
    error_message: Optional[str] = None


def generate_fallback_summary(
    hotel: ClassifiedHotel,
    benchmarks: BenchmarkStats,
    period_label: str = config.REPORTING_PERIOD_LABEL,
    error_reason: Optional[str] = None
) -> GeneratedSummary:
    """
    Deterministic rule-based fallback generator.
    Guarantees 100% factual accuracy, zero hallucinations, and zero downtime
    when LLM APIs are offline or API keys are not supplied.
    """
    currency = config.CURRENCY_SYMBOL
    name = hotel.record.brandname
    rev_formatted = f"{currency}{hotel.record.revenue:,.0f}"
    orders = hotel.record.orders
    aov_formatted = f"{currency}{hotel.aov:,.0f}"
    med_rev_formatted = f"{currency}{benchmarks.median_revenue:,.0f}"

    if hotel.classification == "Data Check":
        subject = f"[Action Required] FUNNOW Weekly Data Sync Check — {name}"
        body = (
            f"Dear {name} Partner Team,\n\n"
            f"During our automated weekly performance sync for the period {period_label}, "
            f"FUNNOW recorded {currency}0 in revenue and 0 bookings for your property.\n\n"
            f"Before our team compiles your weekly yield analysis, please verify whether:\n"
            f"  1. The property was temporarily closed or under scheduled maintenance.\n"
            f"  2. There were genuinely no completed stays during this calendar week.\n"
            f"  3. Your PMS / channel manager integration experienced a sync interruption.\n\n"
            f"Please reply to this email to confirm your property status so we can update your dashboard accurately.\n\n"
            f"Best regards,\n"
            f"FUNNOW Partner Operations Team"
        )

    elif hotel.classification == "Doing Well":
        subject = f"FUNNOW Weekly Partner Briefing: Strong Performance — {name}"
        body = (
            f"Dear {name} Management Team,\n\n"
            f"We are pleased to share your performance briefing for {period_label}.\n\n"
            f"Key Performance Highlights:\n"
            f"  • Total Revenue: {rev_formatted} (Cohort Median: {med_rev_formatted})\n"
            f"  • Confirmed Bookings: {orders} orders (Cohort Median: {benchmarks.median_orders:.0f})\n"
            f"  • Average Order Value: {aov_formatted}\n\n"
            f"Analysis & Observations:\n"
            f"Your property performed strongly this week, meeting or exceeding cohort benchmarks in both revenue "
            f"and booking volume. Your Average Order Value reflects solid guest spending and steady demand.\n\n"
            f"Strategic Recommendations:\n"
            f"  • Maintain current inventory availability to capture high-intent travelers.\n"
            f"  • Review weekend vs. weekday availability to further maximize peak-time room rates.\n\n"
            f"Thank you for your valued partnership with FUNNOW.\n\n"
            f"Warm regards,\n"
            f"FUNNOW Partner Growth Team"
        )

    else:  # Needs Improvement
        subject = f"FUNNOW Weekly Partner Briefing: Optimization Opportunities — {name}"
        
        # Tailor specific guidance based on AOV vs volume balance
        if hotel.record.revenue >= benchmarks.median_revenue:
            guidance = (
                f"While your total revenue ({rev_formatted}) is healthy, your order volume ({orders}) "
                f"trailed the cohort median of {benchmarks.median_orders:.0f}. "
                f"Because your Average Order Value ({aov_formatted}) is high, focusing on targeted mid-week "
                f"campaigns or flexible cancellation policies could help lift overall booking volume."
            )
        elif hotel.record.orders >= benchmarks.median_orders:
            guidance = (
                f"Your property generated robust order volume ({orders} bookings), but your total revenue "
                f"({rev_formatted}) was below the cohort median of {med_rev_formatted}. "
                f"Your Average Order Value stands at {aov_formatted}. "
                f"We recommend exploring room upgrade add-ons, bundled packages, or modest adjustments to base rates "
                f"to capture higher yield per stay."
            )
        else:
            guidance = (
                f"This week's revenue ({rev_formatted}) and booking volume ({orders}) both landed below the "
                f"cohort medians ({med_rev_formatted} and {benchmarks.median_orders:.0f} orders). "
                f"We recommend reviewing your listing photos, checking competitive rate parity on FUNNOW, "
                f"and opening up last-minute flash availability to stimulate conversion."
            )

        body = (
            f"Dear {name} Management Team,\n\n"
            f"Here is your weekly performance summary for {period_label}.\n\n"
            f"Weekly Performance Overview:\n"
            f"  • Total Revenue: {rev_formatted} (Cohort Median: {med_rev_formatted})\n"
            f"  • Confirmed Bookings: {orders} orders (Cohort Median: {benchmarks.median_orders:.0f})\n"
            f"  • Average Order Value: {aov_formatted}\n\n"
            f"Analysis & Action Plan:\n"
            f"{guidance}\n\n"
            f"Our account management team is available if you would like support setting up promotional campaigns.\n\n"
            f"Warm regards,\n"
            f"FUNNOW Partner Growth Team"
        )

    return GeneratedSummary(
        subject=subject,
        body=body,
        is_ai_generated=False,
        generation_method="FALLBACK_DETERMINISTIC",
        error_message=error_reason
    )


def generate_summary(
    hotel: ClassifiedHotel,
    benchmarks: BenchmarkStats,
    period_label: str = config.REPORTING_PERIOD_LABEL
) -> GeneratedSummary:
    """
    Primary summary generator.
    Attempts LLM API generation with strict system prompt guardrails.
    Gracefully and transparently falls back to deterministic rules upon any failure.
    """
    # 1. Check for Gemini API Key
    if config.GEMINI_API_KEY:
        try:
            return _generate_with_gemini(hotel, benchmarks, period_label)
        except Exception as e:
            logger.warning(f"Gemini API generation failed for {hotel.record.brandname}: {e}")
            return generate_fallback_summary(
                hotel, benchmarks, period_label, error_reason=f"Gemini API error: {str(e)}"
            )

    # 2. Check for OpenAI API Key
    if config.OPENAI_API_KEY:
        try:
            return _generate_with_openai(hotel, benchmarks, period_label)
        except Exception as e:
            logger.warning(f"OpenAI API generation failed for {hotel.record.brandname}: {e}")
            return generate_fallback_summary(
                hotel, benchmarks, period_label, error_reason=f"OpenAI API error: {str(e)}"
            )

    # 3. No API Key configured -> Fallback rule-based generator
    return generate_fallback_summary(
        hotel,
        benchmarks,
        period_label,
        error_reason="No LLM API key configured (operating in deterministic fallback mode)"
    )


def _build_prompt_context(hotel: ClassifiedHotel, benchmarks: BenchmarkStats, period_label: str) -> dict:
    """Constructs the strictly grounded data payload for the LLM."""
    return {
        "hotel_name": hotel.record.brandname,
        "reporting_period": period_label,
        "revenue": hotel.record.revenue,
        "revenue_formatted": f"{config.CURRENCY_SYMBOL}{hotel.record.revenue:,.0f}",
        "orders": hotel.record.orders,
        "aov_formatted": f"{config.CURRENCY_SYMBOL}{hotel.aov:,.0f}",
        "cohort_median_revenue": f"{config.CURRENCY_SYMBOL}{benchmarks.median_revenue:,.0f}",
        "cohort_median_orders": benchmarks.median_orders,
        "classification": hotel.classification,
        "performance_reasons": hotel.performance_reasons,
        "coaching_theme": hotel.coaching_theme,
    }


SYSTEM_PROMPT = """You are an automated partner communications assistant at FUNNOW, an online travel & hotel booking platform.
Your task is to generate a personalized, professional, and friendly Monday morning weekly performance email for a hotel partner.

CRITICAL FACTUAL SAFEGUARDS:
1. ONLY reference the exact numbers and facts provided in the JSON input.
2. DO NOT invent previous week comparisons, historical trends, occupancy percentages, or growth rates. The dataset contains single-week snapshots only.
3. DO NOT mention or disclose any other hotel's name, revenue, or specific metrics. Refer only to general 'cohort medians'.
4. If classification is 'Data Check', maintain a helpful, neutral tone asking for status confirmation (closure, zero stays, or PMS feed sync issue).
5. If classification is 'Doing Well', be encouraging and offer yield maximization tips.
6. If classification is 'Needs Improvement', be supportive, polite, and offer constructive tips.

You must respond in valid JSON with exactly two fields:
{
  "subject": "Email subject line",
  "body": "Formatted email body text including salutation and sign-off"
}
"""


def _generate_with_gemini(hotel: ClassifiedHotel, benchmarks: BenchmarkStats, period_label: str) -> GeneratedSummary:
    """Invokes Google Gemini API with structured output."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    context_data = _build_prompt_context(hotel, benchmarks, period_label)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Data Context:\n{json.dumps(context_data, indent=2)}\n\nGenerate the weekly briefing email.",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.2,
        )
    )

    data = json.loads(response.text)
    return GeneratedSummary(
        subject=data["subject"],
        body=data["body"],
        is_ai_generated=True,
        generation_method="GEMINI_API"
    )


def _generate_with_openai(hotel: ClassifiedHotel, benchmarks: BenchmarkStats, period_label: str) -> GeneratedSummary:
    """Invokes OpenAI API with JSON mode."""
    from openai import OpenAI

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    context_data = _build_prompt_context(hotel, benchmarks, period_label)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Data Context:\n{json.dumps(context_data, indent=2)}\n\nGenerate the email."}
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    content = response.choices[0].message.content
    data = json.loads(content)
    return GeneratedSummary(
        subject=data["subject"],
        body=data["body"],
        is_ai_generated=True,
        generation_method="OPENAI_API"
    )
