"""
Decision Logging API routes.

Endpoints:
  POST /api/decisions          — log a buyer decision (approve / skip / override)
  GET  /api/decisions/summary  — aggregate decision counts + impact
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from db import get_conn

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/decisions", tags=["decisions"])

VALID_ACTIONS = {"approve", "skip", "override"}
VALID_QUEUE_TYPES = {
    "RETURN_WINDOW_CLOSING",
    "STOCKOUT_RISK",
    "DEAD_STOCK",
    "DEMAND_DECLINING",
    "OVER_ORDER_RISK",
}


class DecisionRequest(BaseModel):
    sku_id: str
    queue_type: str
    action: str  # approve | skip | override
    override_qty: Optional[int] = None
    override_reason: Optional[str] = None
    recommended_qty: Optional[int] = None
    financial_impact_lei: Optional[float] = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_ACTIONS:
            raise ValueError(f"action must be one of {VALID_ACTIONS}")
        return v

    @field_validator("queue_type")
    @classmethod
    def validate_queue_type(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in VALID_QUEUE_TYPES:
            raise ValueError(f"queue_type must be one of {VALID_QUEUE_TYPES}")
        return v


@router.post("")
def log_decision(req: DecisionRequest):
    """Record a buyer decision from the Morning Queue."""
    if req.action == "override" and req.override_qty is None:
        raise HTTPException(status_code=422, detail="override_qty is required when action is 'override'")

    conn = get_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO decisions (sku_id, queue_type, action, override_qty, override_reason,
                                   recommended_qty, financial_impact_lei)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                req.sku_id,
                req.queue_type,
                req.action,
                req.override_qty,
                req.override_reason,
                req.recommended_qty,
                req.financial_impact_lei,
            ),
        )
        conn.commit()
        decision_id = cur.lastrowid
    finally:
        conn.close()

    log.info("Decision logged: %s %s on %s (id=%d)", req.action, req.queue_type, req.sku_id, decision_id)
    return {
        "decision_id": decision_id,
        "status": "recorded",
        "action": req.action,
        "sku_id": req.sku_id,
    }


@router.get("/summary")
def decisions_summary(today_only: bool = True):
    """Aggregate decision counts and financial impact."""
    conn = get_conn()
    try:
        where = "WHERE DATE(decided_at) = DATE('now')" if today_only else ""

        row = conn.execute(f"""
            SELECT
                COUNT(*)                                              AS total,
                SUM(CASE WHEN action = 'approve'  THEN 1 ELSE 0 END) AS approved,
                SUM(CASE WHEN action = 'skip'     THEN 1 ELSE 0 END) AS skipped,
                SUM(CASE WHEN action = 'override' THEN 1 ELSE 0 END) AS overridden,
                COALESCE(SUM(CASE WHEN action = 'approve' THEN financial_impact_lei ELSE 0 END), 0)  AS approved_impact_lei,
                COALESCE(SUM(CASE WHEN action = 'skip'    THEN financial_impact_lei ELSE 0 END), 0)  AS skipped_impact_lei,
                COALESCE(SUM(CASE WHEN action = 'override' THEN financial_impact_lei ELSE 0 END), 0) AS overridden_impact_lei
            FROM decisions
            {where}
        """).fetchone()

        # Breakdown by queue type
        type_rows = conn.execute(f"""
            SELECT queue_type,
                   COUNT(*) AS count,
                   COALESCE(SUM(financial_impact_lei), 0) AS impact_lei
            FROM decisions
            {where}
            GROUP BY queue_type
            ORDER BY count DESC
        """).fetchall()

        # Recent decisions (last 10)
        recent = conn.execute(f"""
            SELECT id, sku_id, queue_type, action, override_qty, financial_impact_lei, decided_at
            FROM decisions
            {where}
            ORDER BY decided_at DESC
            LIMIT 10
        """).fetchall()

    finally:
        conn.close()

    return {
        "today_only": today_only,
        "total": row["total"],
        "approved": row["approved"],
        "skipped": row["skipped"],
        "overridden": row["overridden"],
        "approved_impact_lei": round(row["approved_impact_lei"], 2),
        "skipped_impact_lei": round(row["skipped_impact_lei"], 2),
        "overridden_impact_lei": round(row["overridden_impact_lei"], 2),
        "by_queue_type": [
            {"queue_type": r["queue_type"], "count": r["count"], "impact_lei": round(r["impact_lei"], 2)}
            for r in type_rows
        ],
        "recent": [
            {
                "id": r["id"],
                "sku_id": r["sku_id"],
                "queue_type": r["queue_type"],
                "action": r["action"],
                "override_qty": r["override_qty"],
                "financial_impact_lei": r["financial_impact_lei"],
                "decided_at": r["decided_at"],
            }
            for r in recent
        ],
    }
