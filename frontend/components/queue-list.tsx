"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { formatLei } from "@/lib/format";
import type { QueueItem } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type StatusTab = "ALL" | "URGENT" | "REVIEW" | "INFO";
type QueueType = "ALL" | "RETURN_WINDOW_CLOSING" | "STOCKOUT_RISK" | "DEAD_STOCK" | "DEMAND_DECLINING" | "OVER_ORDER_RISK";

const STATUS_CONFIG = {
  URGENT: { bg: "bg-red-100",   text: "text-red-700",   dot: "bg-red-500"   },
  REVIEW: { bg: "bg-amber-100", text: "text-amber-700", dot: "bg-amber-500" },
  INFO:   { bg: "bg-gray-100",  text: "text-gray-600",  dot: "bg-gray-400"  },
};

const TYPE_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  RETURN_WINDOW_CLOSING: { label: "Return Window Closing", bg: "bg-red-50",    text: "text-red-600"    },
  STOCKOUT_RISK:         { label: "Stockout Risk",         bg: "bg-orange-50", text: "text-orange-600" },
  DEAD_STOCK:            { label: "Dead Stock",            bg: "bg-amber-50",  text: "text-amber-700"  },
  DEMAND_DECLINING:      { label: "Demand Declining",      bg: "bg-yellow-50", text: "text-yellow-700" },
  OVER_ORDER_RISK:       { label: "Over-Order Risk",       bg: "bg-yellow-50", text: "text-yellow-600" },
};

const TYPE_LABELS: Record<QueueType, string> = {
  ALL:                   "All Types",
  RETURN_WINDOW_CLOSING: "Return Window",
  STOCKOUT_RISK:         "Stockout Risk",
  DEAD_STOCK:            "Dead Stock",
  DEMAND_DECLINING:      "Demand Declining",
  OVER_ORDER_RISK:       "Over-Order Risk",
};

// Unique render key — includes `what` to differentiate same SKU across multiple stores
function itemRenderKey(item: QueueItem) {
  return `${item.queue_type}-${item.sku_id ?? item.supplier_id ?? ""}-${item.what}`;
}

// Action key — groups all instances of the same SKU+type together for actioned tracking
function itemActionKey(item: QueueItem) {
  return `${item.queue_type}-${item.sku_id ?? item.supplier_id ?? ""}`;
}

const PAGE_SIZE = 50;

export function QueueList({
  items,
  urgentCount,
  reviewCount,
  infoCount,
  aiAvailable,
}: {
  items: QueueItem[];
  urgentCount: number;
  reviewCount: number;
  infoCount: number;
  aiAvailable: boolean;
}) {
  const [statusTab, setStatusTab] = useState<StatusTab>("ALL");
  const [typeFilter, setTypeFilter] = useState<QueueType>("ALL");
  const [shown, setShown] = useState(PAGE_SIZE);
  const [actionedIds, setActionedIds] = useState<Set<string>>(new Set());

  function handleActioned(key: string) {
    setActionedIds((prev) => new Set([...prev, key]));
  }

  const filtered = items
    .filter((i) => statusTab === "ALL" || i.status === statusTab)
    .filter((i) => typeFilter === "ALL" || i.queue_type === typeFilter);

  // Actioned items sink to the bottom
  const sorted = [...filtered].sort((a, b) => {
    const aActioned = actionedIds.has(itemActionKey(a));
    const bActioned = actionedIds.has(itemActionKey(b));
    if (aActioned === bActioned) return 0;
    return aActioned ? 1 : -1;
  });

  const visible = sorted.slice(0, shown);
  const hasMore = shown < sorted.length;

  return (
    <div className="space-y-4">
      {/* Status tabs */}
      <div className="flex gap-1 border-b border-gray-200 pb-0">
        {(
          [
            { key: "ALL",    label: "All",    count: items.length },
            { key: "URGENT", label: "Urgent", count: urgentCount  },
            { key: "REVIEW", label: "Review", count: reviewCount  },
            { key: "INFO",   label: "Info",   count: infoCount    },
          ] as const
        ).map(({ key, label, count }) => (
          <button
            key={key}
            onClick={() => { setStatusTab(key); setShown(PAGE_SIZE); }}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              statusTab === key
                ? "border-gray-900 text-gray-900"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {label}
            <span
              className={`ml-2 text-xs px-1.5 py-0.5 rounded-full ${
                key === "URGENT"
                  ? "bg-red-100 text-red-700"
                  : key === "REVIEW"
                  ? "bg-amber-100 text-amber-700"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              {count}
            </span>
          </button>
        ))}
      </div>

      {/* Type filter pills */}
      <div className="flex flex-wrap gap-2">
        {(Object.keys(TYPE_LABELS) as QueueType[]).map((t) => (
          <button
            key={t}
            onClick={() => { setTypeFilter(t); setShown(PAGE_SIZE); }}
            className={`px-3 py-1.5 rounded-full text-xs transition-colors ${
              typeFilter === t
                ? "bg-gray-900 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {TYPE_LABELS[t]}
          </button>
        ))}
        <span className="ml-auto self-center text-xs text-gray-400">
          {filtered.length} items
          {actionedIds.size > 0 && (
            <span className="ml-2 text-emerald-600 font-medium">{actionedIds.size} actioned</span>
          )}
        </span>
      </div>

      {/* Item list */}
      <div className="space-y-2">
        {visible.map((item) => (
          <QueueCard
            key={itemRenderKey(item)}
            item={item}
            aiAvailable={aiAvailable}
            isActioned={actionedIds.has(itemActionKey(item))}
            onActioned={() => handleActioned(itemActionKey(item))}
          />
        ))}
      </div>

      {/* Load more */}
      {hasMore && (
        <button
          onClick={() => setShown((s) => s + PAGE_SIZE)}
          className="w-full py-3 rounded-xl border border-dashed border-gray-300 text-sm text-gray-500 hover:border-gray-400 hover:text-gray-700 transition-colors"
        >
          Show {Math.min(PAGE_SIZE, sorted.length - shown)} more
          <span className="text-gray-400"> ({sorted.length - shown} remaining)</span>
        </button>
      )}

      {filtered.length === 0 && (
        <div className="py-12 text-center text-sm text-gray-400">
          No items match the current filters.
        </div>
      )}
    </div>
  );
}

// ── Queue card ────────────────────────────────────────────────────────────────

type DecisionPhase =
  | { phase: "idle" }
  | { phase: "override_form" }
  | { phase: "saving"; action: string }
  | { phase: "done"; action: string; override_qty?: number };

function QueueCard({
  item,
  aiAvailable,
  isActioned,
  onActioned,
}: {
  item: QueueItem;
  aiAvailable: boolean;
  isActioned: boolean;
  onActioned: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const [decision, setDecision] = useState<DecisionPhase>({ phase: "idle" });
  const [overrideQty, setOverrideQty] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [decisionError, setDecisionError] = useState<string | null>(null);

  const statusCfg = STATUS_CONFIG[item.status];
  const typeCfg = TYPE_CONFIG[item.queue_type] ?? { label: item.queue_type, bg: "bg-gray-50", text: "text-gray-600" };
  const skuName = item.what.split(" — ")[0];

  function fetchExplanation(e: React.MouseEvent) {
    e.stopPropagation();
    if (explanation || isPending) return;
    startTransition(async () => {
      try {
        const res = await fetch(`${API}/api/explain`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            queue_type: item.queue_type,
            what: item.what,
            why: item.why,
            financial_impact_lei: item.financial_impact_lei,
            recommended_action: item.recommended_action,
            details: item.details,
          }),
        });
        const data = await res.json();
        setExplanation(
          data.explanation ?? "Add GEMINI_API_KEY to backend/.env to enable AI explanations."
        );
      } catch {
        setExplanation("Could not reach the backend.");
      }
    });
  }

  async function submitDecision(action: string, qty?: number, reason?: string) {
    if (!item.sku_id) return;
    setDecision({ phase: "saving", action });
    setDecisionError(null);
    try {
      const body: Record<string, unknown> = {
        sku_id: item.sku_id,
        queue_type: item.queue_type,
        action,
        financial_impact_lei: item.financial_impact_lei ?? null,
      };
      if (action === "override") {
        body.override_qty = qty;
        body.override_reason = reason ?? null;
      }
      const res = await fetch(`${API}/api/decisions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `Error ${res.status}`);
      }
      setDecision({ phase: "done", action, override_qty: qty });
      onActioned();
    } catch (err) {
      setDecisionError(err instanceof Error ? err.message : "Failed to save decision");
      setDecision({ phase: "idle" });
    }
  }

  function handleApprove(e: React.MouseEvent) {
    e.stopPropagation();
    submitDecision("approve");
  }

  function handleSkip(e: React.MouseEvent) {
    e.stopPropagation();
    submitDecision("skip");
  }

  function handleOverrideOpen(e: React.MouseEvent) {
    e.stopPropagation();
    setDecision({ phase: "override_form" });
    setOverrideQty("");
    setOverrideReason("");
  }

  function handleOverrideSubmit(e: React.MouseEvent) {
    e.stopPropagation();
    const qty = parseInt(overrideQty, 10);
    if (!overrideQty || isNaN(qty) || qty < 0) {
      setDecisionError("Enter a valid quantity (0 or more)");
      return;
    }
    setDecisionError(null);
    submitDecision("override", qty, overrideReason.trim() || undefined);
  }

  function handleOverrideCancel(e: React.MouseEvent) {
    e.stopPropagation();
    setDecision({ phase: "idle" });
    setDecisionError(null);
  }

  const DONE_LABELS: Record<string, string> = {
    approve: "✓ Approved",
    skip: "Skipped",
    override: "✓ Overridden",
  };

  const DONE_STYLES: Record<string, string> = {
    approve: "bg-emerald-50 text-emerald-700 border-emerald-200",
    skip: "bg-gray-100 text-gray-500 border-gray-200",
    override: "bg-blue-50 text-blue-700 border-blue-200",
  };

  return (
    <div
      className={`bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-all cursor-pointer ${
        isActioned ? "opacity-60" : ""
      }`}
      onClick={() => setExpanded((e) => !e)}
    >
      <div className="px-5 py-4">
        {/* Top row: status + type + impact */}
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${statusCfg.bg} ${statusCfg.text}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${statusCfg.dot}`} />
              {item.status}
            </span>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${typeCfg.bg} ${typeCfg.text}`}>
              {typeCfg.label}
            </span>
          </div>
          {item.financial_impact_lei > 0 && (
            <span className="text-sm font-semibold text-gray-900">
              {formatLei(item.financial_impact_lei)}
            </span>
          )}
        </div>

        {/* SKU name */}
        {item.sku_id ? (
          <Link
            href={`/sku/${item.sku_id}`}
            onClick={(e) => e.stopPropagation()}
            className="mt-2 block font-semibold text-gray-900 hover:text-blue-700 hover:underline"
          >
            {skuName}
          </Link>
        ) : (
          <p className="mt-2 font-semibold text-gray-900">{skuName}</p>
        )}

        {/* Why */}
        <p className="mt-1 text-sm text-gray-600">{item.why}</p>

        {/* Recommended action + Ask AI */}
        <div className="mt-2 flex items-start justify-between gap-3 flex-wrap">
          <p className="text-sm text-gray-500">
            <span className="font-medium text-gray-700">→ </span>
            {item.recommended_action}
          </p>
          {aiAvailable && !explanation && (
            <button
              onClick={fetchExplanation}
              disabled={isPending}
              className="flex-shrink-0 text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50 transition-colors"
            >
              {isPending ? "Asking AI…" : "Ask AI ✦"}
            </button>
          )}
        </div>

        {/* ── Decision actions ─────────────────────────────────────────── */}
        {item.sku_id && (
          <div
            className="mt-3 pt-3 border-t border-gray-100"
            onClick={(e) => e.stopPropagation()}
          >
            {decision.phase === "idle" && (
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  onClick={handleApprove}
                  className="px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-medium text-emerald-700 hover:bg-emerald-100 transition-colors"
                >
                  ✓ Approve
                </button>
                <button
                  onClick={handleSkip}
                  className="px-3 py-1.5 rounded-lg bg-gray-50 border border-gray-200 text-xs font-medium text-gray-600 hover:bg-gray-100 transition-colors"
                >
                  Skip
                </button>
                <button
                  onClick={handleOverrideOpen}
                  className="px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-200 text-xs font-medium text-blue-700 hover:bg-blue-100 transition-colors"
                >
                  ⚙ Override
                </button>
              </div>
            )}

            {decision.phase === "override_form" && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <input
                    type="number"
                    min="0"
                    value={overrideQty}
                    onChange={(e) => setOverrideQty(e.target.value)}
                    placeholder="Override qty"
                    className="w-28 text-xs px-3 py-1.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-400"
                    onClick={(e) => e.stopPropagation()}
                  />
                  <input
                    type="text"
                    value={overrideReason}
                    onChange={(e) => setOverrideReason(e.target.value)}
                    placeholder="Reason (optional)"
                    className="flex-1 min-w-[140px] text-xs px-3 py-1.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-400"
                    onClick={(e) => e.stopPropagation()}
                  />
                  <button
                    onClick={handleOverrideSubmit}
                    className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 transition-colors"
                  >
                    Confirm
                  </button>
                  <button
                    onClick={handleOverrideCancel}
                    className="px-3 py-1.5 rounded-lg bg-gray-100 text-gray-600 text-xs font-medium hover:bg-gray-200 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {decision.phase === "saving" && (
              <p className="text-xs text-gray-400 animate-pulse">Saving…</p>
            )}

            {decision.phase === "done" && (
              <span
                className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${
                  DONE_STYLES[decision.action] ?? "bg-gray-100 text-gray-600 border-gray-200"
                }`}
              >
                {DONE_LABELS[decision.action] ?? decision.action}
                {decision.action === "override" && decision.override_qty != null && (
                  <span className="ml-1">to {decision.override_qty} units</span>
                )}
              </span>
            )}

            {decisionError && (
              <p className="mt-1 text-xs text-red-600">{decisionError}</p>
            )}
          </div>
        )}

        {/* AI explanation */}
        {explanation && (
          <div
            className="mt-3 rounded-lg bg-blue-50 border border-blue-100 px-4 py-3"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="text-xs font-semibold text-blue-500 mb-1">AI Analysis</p>
            <p className="text-sm text-blue-900 leading-relaxed">{explanation}</p>
          </div>
        )}

        {/* Expanded detail */}
        {expanded && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <DetailSection item={item} />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Detail section (varies by queue_type) ────────────────────────────────────

function DetailSection({ item }: { item: QueueItem }) {
  const d = item.details as Record<string, string | number | boolean | null | undefined>;

  if (item.queue_type === "RETURN_WINDOW_CLOSING" || item.queue_type === "DEAD_STOCK") {
    return (
      <div className="flex gap-6 text-sm text-gray-600 flex-wrap">
        {d.store_id != null && <Detail label="Store" value={String(d.store_id)} />}
        {d.days_inactive != null && <Detail label="Days Inactive" value={`${d.days_inactive}d`} />}
        {d.trajectory != null && (
          <Detail label="Trajectory" value={String(d.trajectory).replace(/_/g, " ")} />
        )}
        {d.return_window_days_remaining != null && (
          <Detail label="Return Window" value={`${d.return_window_days_remaining} days left`} />
        )}
        {item.supplier_id != null && <Detail label="Supplier" value={item.supplier_id} />}
        {item.sku_id != null && <Detail label="SKU ID" value={item.sku_id} />}
      </div>
    );
  }

  if (item.queue_type === "STOCKOUT_RISK") {
    return (
      <div className="flex gap-6 text-sm text-gray-600 flex-wrap">
        {d.supplier_name != null && <Detail label="Supplier" value={String(d.supplier_name)} />}
        {d.promised_lead_time_days != null && (
          <Detail label="Promised Lead Time" value={`${d.promised_lead_time_days}d`} />
        )}
        {d.actual_lead_time_days != null && (
          <Detail label="Actual Lead Time" value={`${d.actual_lead_time_days}d`} emphasis />
        )}
        {item.sku_id != null && <Detail label="SKU ID" value={item.sku_id} />}
      </div>
    );
  }

  if (item.queue_type === "DEMAND_DECLINING") {
    return (
      <div className="flex gap-6 text-sm text-gray-600 flex-wrap">
        {d.trend_slope != null && (
          <Detail label="Weekly Slope" value={`${Number(d.trend_slope).toFixed(1)} units/wk`} />
        )}
        {d.forecast_4_weeks != null && (
          <Detail label="Real Forecast (4w)" value={`${Number(d.forecast_4_weeks).toFixed(0)} units`} />
        )}
        {d.v_tool_estimate != null && (
          <Detail label="V's Tool Estimate" value={`${Number(d.v_tool_estimate).toFixed(0)} units`} emphasis />
        )}
        {item.sku_id && <Detail label="SKU ID" value={item.sku_id} />}
      </div>
    );
  }

  if (item.queue_type === "OVER_ORDER_RISK") {
    return (
      <div className="flex gap-6 text-sm text-gray-600 flex-wrap">
        {d.return_rate != null && (
          <Detail label="Return Rate" value={`${(Number(d.return_rate) * 100).toFixed(0)}%`} emphasis />
        )}
        {d.apparent_demand != null && (
          <Detail label="Apparent Demand" value={`${Number(d.apparent_demand).toFixed(0)}/mo`} />
        )}
        {d.real_demand != null && (
          <Detail label="Real Demand" value={`${Number(d.real_demand).toFixed(0)}/mo`} />
        )}
        {item.sku_id && <Detail label="SKU ID" value={item.sku_id} />}
      </div>
    );
  }

  return null;
}

function Detail({
  label,
  value,
  emphasis = false,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-gray-400">{label}</p>
      <p className={`font-medium ${emphasis ? "text-red-600" : "text-gray-800"}`}>{value}</p>
    </div>
  );
}
