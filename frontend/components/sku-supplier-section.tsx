import type { SkuProfile } from "@/lib/api";

const STATUS_CONFIG = {
  GREEN:  { bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-700", label: "Reliable" },
  YELLOW: { bg: "bg-amber-50",   border: "border-amber-200",   text: "text-amber-700",   label: "At Risk" },
  RED:    { bg: "bg-red-50",     border: "border-red-200",     text: "text-red-700",     label: "Critical" },
};

const TREND_LABELS: Record<string, string> = {
  IMPROVING: "↑ Improving",
  STABLE:    "→ Stable",
  WORSENING: "↓ Worsening",
};

const TREND_COLORS: Record<string, string> = {
  IMPROVING: "text-emerald-600",
  STABLE:    "text-gray-500",
  WORSENING: "text-red-600",
};

export function SkuSupplierSection({ sku }: { sku: SkuProfile }) {
  if (!sku.supplier) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-2">Supplier</h2>
        <p className="text-sm text-gray-400">No supplier order history found for this SKU.</p>
      </div>
    );
  }

  const s = sku.supplier;
  const cfg = STATUS_CONFIG[s.status];

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <h2 className="text-base font-semibold text-gray-900 mb-4">Supplier</h2>

      <div className={`rounded-xl border ${cfg.border} ${cfg.bg} p-4 mb-4`}>
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <p className="text-sm font-semibold text-gray-900">{s.supplier_name}</p>
            <p className="text-xs text-gray-500 mt-0.5">{s.supplier_id}</p>
          </div>
          <div className="text-right">
            <p className={`text-2xl font-bold ${cfg.text}`}>{Math.round(s.reliability_score)}</p>
            <p className={`text-xs font-semibold ${cfg.text}`}>{cfg.label}</p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Promised lead time" value={`${Math.round(s.avg_promised_lead_time_days)}d`} />
          <Stat
            label="Actual lead time"
            value={`${Math.round(s.avg_actual_lead_time_days)}d`}
            highlight={s.lead_time_gap_days > 5}
          />
          <Stat
            label="Lead time gap"
            value={`+${Math.round(s.lead_time_gap_days)}d`}
            highlight={s.lead_time_gap_days > 5}
          />
          <div className="rounded-lg bg-white bg-opacity-60 px-3 py-2">
            <p className="text-xs text-gray-500">Trend</p>
            <p className={`text-sm font-semibold mt-0.5 ${TREND_COLORS[s.trend] ?? "text-gray-700"}`}>
              {TREND_LABELS[s.trend] ?? s.trend}
            </p>
          </div>
        </div>
      </div>

      {/* Stockout risk for this specific SKU */}
      {s.stockout_risk ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm font-semibold text-red-800 mb-1">Stockout Risk for this SKU</p>
          <p className="text-sm text-red-700">{s.stockout_risk.message}</p>
          <p className="text-xs text-red-600 mt-1">
            Order should have been placed {Math.round(s.stockout_risk.days_overdue)} days earlier
          </p>
        </div>
      ) : (
        <p className="text-sm text-gray-400">No stockout risk detected for this SKU with this supplier.</p>
      )}
    </div>
  );
}

function Stat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`rounded-lg px-3 py-2 ${highlight ? "bg-red-100" : "bg-white bg-opacity-60"}`}>
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-sm font-semibold mt-0.5 ${highlight ? "text-red-700" : "text-gray-800"}`}>{value}</p>
    </div>
  );
}
