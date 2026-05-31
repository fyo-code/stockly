"""
AI Explanation endpoint.

POST /api/explain   — generate an AI explanation for a single queue item
GET  /api/explain/status — check if API key is configured
"""

import logging
from fastapi import APIRouter
from pydantic import BaseModel

from agents.reasoner import explain_queue_item, _get_client

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/explain", tags=["explain"])


class ExplainRequest(BaseModel):
    queue_type: str
    what: str
    why: str
    financial_impact_lei: float = 0
    recommended_action: str = ""
    details: dict = {}


@router.get("/status")
def explain_status():
    """Check whether Gemini API is configured and reachable."""
    client = _get_client()
    return {"available": client is not None}


@router.post("")
def explain_item(body: ExplainRequest):
    """
    Generate a plain-language AI explanation for a queue item.

    Returns:
        explanation — AI-generated text, or None if API key is not set
        source      — "gemini" | "unavailable"
    """
    item = body.model_dump()
    explanation = explain_queue_item(item)

    return {
        "explanation": explanation,
        "source": "gemini" if explanation is not None else "unavailable",
    }
