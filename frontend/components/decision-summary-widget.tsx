import Link from "next/link";
import { formatLei } from "@/lib/format";
import type { DecisionSummary } from "@/lib/api";

const QUEUE_TYPE_LABELS: Record<string, string> = {
  RETURN_WINDOW_CLOSING: "Return Window",
  STOCKOUT_RISK:         "Stockout Risk",
  DEAD_STOCK:            "Dead Stock",
  DEMAND_DECLINING:      "Demand Declining",
  OVER_ORDER_RISK:       "Over-Order Risk",
};

const ACTION_CONFIG = {
  approve:  { label: "Approved",   bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  skip:     { label: "Skipped",    bg: "bg-gray-50",    text: "text-gray-500",    border: "border-gray-200"   },
  override: { label: "Overridden", bg: "bg-blue-50",    text: "text-blue-700",    border: "border-blue-200"   },
};

export function DecisionSummaryWidget({ data }: { data: DecisionSummary | null }) {
  if (!data) return null;

  const totalImpact = data.approved_impact_lei + data.skipped_impact_lei + data.overridden_impact_lei;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-gray-900">Today&apos;s Decisions</h2>
          <p className="text-xs text-gray-400 mt-0.5">Actions recorded from the Morning Queue</p>
        </div>
        <Link
          href="/queue"
          className="text-xs text-gray-500 hover:text-gray-800 transition-colors"
        >
          Go to queue →
        </Link>
      </div>

      {data.total === 0 ? (
        <div className="px-6 py-8 text-center">
          <p className="text-sm text-gray-400">No decisions recorded yet today.</p>
          <Link
            href="/queue"
            className="mt-2 inline-block text-xs text-blue-600 hover:text-blue-800 font-medium"
          >
            Open Morning Queue →
          </Link>
        </div>
      ) : (
        <div className="px-6 py-5 space-y-4">
          {/* Action count badges */}
          <div className="flex flex-wrap gap-3">
            {(["approve", "skip", "override"] as const).map((action) => {
              const count = data[`${action}d` as "approved" | "skipped" | "overridden"];
              if (count === 0) return null;
              const cfg = ACTION_CONFIG[action];
              const impact = data[`${action === "approve" ? "approved" : action === "skip" ? "skipped" : "overridden"}_impact_lei` as keyof DecisionSummary] as number;
              return (
                <div
                  key={action}
                  className={`flex items-center gap-3 rounded-xl border ${cfg.border} ${cfg.bg} px-4 py-3`}
                >
                  <div>
                    <p className={`text-2xl font-bold ${cfg.text}`}>{count}</p>
                    <p className={`text-xs font-medium ${cfg.text}`}>{cfg.label}</p>
                  </div>
                  {impact > 0 && (
                    <div className="border-l border-current border-opacity-20 pl-3">
                      <p className={`text-sm font-semibold ${cfg.text}`}>{formatLei(impact)}</p>
                      <p className={`text-xs ${cfg.text} opacity-70`}>impact</p>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Total summary pill */}
            <div className="ml-auto flex items-center gap-2 text-right">
              <div>
                <p className="text-2xl font-bold text-gray-900">{data.total}</p>
                <p className="text-xs text-gray-400">total decisions</p>
              </div>
              {totalImpact > 0 && (
                <div className="border-l border-gray-200 pl-3">
                  <p className="text-sm font-semibold text-gray-700">{formatLei(totalImpact)}</p>
                  <p className="text-xs text-gray-400">total impact</p>
                </div>
              )}
            </div>
          </div>

          {/* Breakdown by queue type */}
          {data.by_queue_type.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {data.by_queue_type.map((t) => (
                <span
                  key={t.queue_type}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-gray-100 text-xs text-gray-600"
                >
                  <span className="font-semibold">{t.count}</span>
                  {QUEUE_TYPE_LABELS[t.queue_type] ?? t.queue_type}
                </span>
              ))}
            </div>
          )}

          {/* Recent decisions list */}
          {data.recent.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Recent</p>
              <div className="space-y-1">
                {data.recent.slice(0, 5).map((d) => {
                  const cfg = ACTION_CONFIG[d.action as keyof typeof ACTION_CONFIG] ?? ACTION_CONFIG.skip;
                  return (
                    <div key={d.id} className="flex items-center justify-between text-xs text-gray-600 py-1 border-b border-gray-50 last:border-0">
                      <div className="flex items-center gap-2">
                        <span className={`font-semibold ${cfg.text}`}>{cfg.label}</span>
                        <Link
                          href={`/sku/${d.sku_id}`}
                          className="text-gray-700 hover:text-blue-700 hover:underline"
                        >
                          {d.sku_id}
                        </Link>
                        <span className="text-gray-400">·</span>
                        <span className="text-gray-400">{QUEUE_TYPE_LABELS[d.queue_type] ?? d.queue_type}</span>
                        {d.action === "override" && d.override_qty != null && (
                          <span className="text-blue-600">→ {d.override_qty} units</span>
                        )}
                      </div>
                      <span className="text-gray-300 tabular-nums">
                        {d.decided_at.split(" ")[1]?.slice(0, 5)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
