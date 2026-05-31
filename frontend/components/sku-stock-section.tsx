import { formatLei } from "@/lib/format";
import type { SkuProfile } from "@/lib/api";

export function SkuStockSection({ sku }: { sku: SkuProfile }) {
  const { dead_stock, coverage, store_breakdown, current_stock } = sku;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <h2 className="text-base font-semibold text-gray-900 mb-4">Stock & Coverage</h2>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-5">
        <Metric label="Total stock" value={`${current_stock} units`} />
        <Metric
          label="Weeks of coverage"
          value={coverage ? `${coverage.weeks_of_coverage}w` : "—"}
          highlight={coverage?.reorder_needed}
          highlightColor="red"
        />
        <Metric
          label="Supplier lead time"
          value={coverage ? `${coverage.lead_time_weeks}w` : "—"}
        />
        <Metric
          label="Reorder needed"
          value={coverage ? (coverage.reorder_needed ? "Yes" : "No") : "—"}
          highlight={coverage?.reorder_needed}
          highlightColor="red"
        />
      </div>

      {/* Reorder alert */}
      {coverage?.reorder_needed && (
        <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3">
          <p className="text-sm font-medium text-red-800">
            Stock covers {coverage.weeks_of_coverage} weeks — supplier lead time is {coverage.lead_time_weeks} weeks.
            Reorder now to avoid stockout.
          </p>
        </div>
      )}

      {/* Store breakdown */}
      <div>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">By store</p>
        <div className="space-y-2">
          {store_breakdown.map((s) => (
            <div key={s.store_id} className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-2.5">
              <span className="text-sm text-gray-700 font-medium">{s.store_id}</span>
              <span className="text-sm text-gray-900 font-semibold">{s.units_in_stock} units</span>
            </div>
          ))}
        </div>
      </div>

      {/* Dead stock section */}
      {dead_stock && (
        <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <p className="text-sm font-semibold text-amber-800">
                Dead Stock — {dead_stock.trajectory.replace("_", " ")}
              </p>
              <p className="text-xs text-amber-700 mt-0.5">
                Inactive for {dead_stock.days_inactive} days across all stores
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm font-bold text-amber-800">{formatLei(dead_stock.total_capital_at_risk_lei)}</p>
              <p className="text-xs text-amber-600">capital at risk</p>
            </div>
          </div>

          {dead_stock.return_window_open ? (
            <div className={`mt-3 text-xs font-medium ${dead_stock.return_window_urgent ? "text-red-700" : "text-amber-700"}`}>
              {dead_stock.return_window_urgent
                ? `⚠ Return window closes in ${dead_stock.return_window_days_remaining} days — act now`
                : `Return window open — ${formatLei(dead_stock.total_budget_unlock_lei)} recoverable via supplier return`}
            </div>
          ) : (
            <p className="mt-3 text-xs text-amber-600">Return window closed — consider markdowns or liquidation</p>
          )}
        </div>
      )}
    </div>
  );
}

function Metric({
  label, value, highlight, highlightColor,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  highlightColor?: "red" | "amber";
}) {
  const bg = highlight
    ? highlightColor === "red" ? "bg-red-50 border-red-100" : "bg-amber-50 border-amber-100"
    : "bg-gray-50 border-gray-100";
  const textColor = highlight
    ? highlightColor === "red" ? "text-red-700" : "text-amber-700"
    : "text-gray-900";

  return (
    <div className={`rounded-lg p-3 border ${bg}`}>
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-lg font-bold mt-0.5 ${textColor}`}>{value}</p>
    </div>
  );
}
