"""
AI Reasoning Layer — Gemini API integration.

Takes a queue item (dead stock, stockout risk, demand decline, etc.)
and generates a plain-language explanation for the buyer.

Falls back gracefully if GEMINI_API_KEY is not set.
"""

import logging
import os

log = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"
MAX_TOKENS = 1024  # Gemini 2.5 Flash uses thinking tokens internally; 1024 covers reasoning + 2-sentence output

SYSTEM_INSTRUCTION = (
    "You are a supply chain analyst for Mobexpert, a Romanian furniture retailer. "
    "You write concise, direct alerts for buyers who need to act fast. "
    "Always use specific numbers. Never use filler phrases like 'it is important to' or 'please note'."
)


def _get_client():
    """Return Gemini client, or None if key is missing."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return None
    try:
        from google import genai  # lazy import so server starts without key
        return genai.Client(api_key=key)
    except Exception as e:
        log.warning("Failed to initialise Gemini client: %s", e)
        return None


def explain_queue_item(item: dict) -> str | None:
    """
    Generate a 2-sentence plain-language explanation for a queue item.

    Returns:
        str  — explanation text if Gemini API is available
        None — if API key is not configured (caller should show raw 'why' text)
    """
    client = _get_client()
    if not client:
        return None

    prompt = _build_prompt(item)

    try:
        from google import genai
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=MAX_TOKENS,
            ),
        )
        text = response.text
        if not text:
            log.warning("Gemini returned empty response")
            return None
        return text.strip()
    except Exception as e:
        log.warning("Gemini API call failed: %s", e)
        return None


def _build_prompt(item: dict) -> str:
    queue_type = item.get("queue_type", "")
    what       = item.get("what", "")
    why        = item.get("why", "")
    impact     = item.get("financial_impact_lei", 0)
    action     = item.get("recommended_action", "")
    details    = item.get("details") or {}

    # Extra context per type
    extra = _type_context(queue_type, details)

    return f"""Write exactly 2 sentences explaining this supply chain alert to a buyer.

Alert: {queue_type.replace("_", " ")}
Item: {what}
Data: {why}{extra}
Financial impact: {impact:,.0f} lei
Action: {action}

Sentence 1 — what is happening and why it costs money.
Sentence 2 — what to do right now and what it achieves (use the lei number).
No filler. No bullet points. Just 2 direct sentences."""


def _type_context(queue_type: str, details: dict) -> str:
    lines = []

    if queue_type == "RETURN_WINDOW_CLOSING":
        days = details.get("return_window_days_remaining")
        if days is not None:
            lines.append(f"Return window: {days} days remaining before it closes permanently.")

    elif queue_type == "STOCKOUT_RISK":
        promised = details.get("promised_lead_time_days")
        actual   = details.get("actual_lead_time_days")
        if promised and actual:
            lines.append(
                f"Supplier promised {promised:.0f}-day lead time, actual average is {actual:.0f} days."
            )

    elif queue_type == "DEMAND_DECLINING":
        slope = details.get("trend_slope")
        v_est = details.get("v_tool_estimate")
        real  = details.get("forecast_4_weeks")
        if slope:
            lines.append(f"Demand dropping {abs(slope):.1f} units/week.")
        if v_est and real:
            lines.append(
                f"V's tool would order {v_est:.0f} units; real forecast is {real:.0f} units."
            )

    elif queue_type == "OVER_ORDER_RISK":
        rate = details.get("return_rate")
        if rate:
            lines.append(f"Product has {rate * 100:.0f}% return rate — apparent demand is inflated.")

    elif queue_type == "DEAD_STOCK":
        days = details.get("days_inactive")
        traj = details.get("trajectory", "")
        if days:
            lines.append(f"Inactive {days} days. Trajectory: {traj.replace('_', ' ')}.")

    return ("\nContext: " + " ".join(lines)) if lines else ""
