import { DemandChart } from "@/components/demand-chart";
import { formatLei } from "@/lib/format";
import type { SkuProfile } from "@/lib/api";

export function SkuDemandSection({ sku }: { sku: SkuProfile }) {
  if (!sku.demand) {
    return (
      <Section title="Demand Forecast">
        <p className="text-sm text-gray-400">Insufficient sales history to generate a forecast for this SKU.</p>
      </Section>
    );
  }

  const d = sku.demand;
  const gapDirection = d.gap_lei > 0 ? "over-order" : "under-order";
  const gapColor = d.gap_lei > 0 ? "text-red-600" : "text-emerald-600";

  return (
    <Section title="Demand Forecast">
      {/* KPI row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-6">
        <Metric label="Real demand / mo" value={Math.round(d.real_demand_monthly).toString()} sub="returns stripped" />
        <Metric label="Apparent demand / mo" value={Math.round(d.apparent_demand_monthly).toString()} sub="gross sales" />
        <Metric label="Forecast 4 weeks" value={Math.round(d.forecast_4_weeks).toString()} sub="trend-adjusted" highlight />
        <Metric label="Forecast 8 weeks" value={Math.round(d.forecast_8_weeks).toString()} sub="trend-adjusted" />
      </div>

      {/* Chart */}
      <DemandChart
        skuName={sku.sku_name}
        weeklyHistory={d.weekly_history}
        forecastWeekly={d.forecast_weekly}
        trendStatus={d.trend_status}
      />

      {/* V's tool comparison */}
      <div className="mt-4 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 flex flex-wrap gap-6 items-center">
        <div>
          <p className="text-xs text-gray-500">V&apos;s tool estimate (4 weeks)</p>
          <p className="text-sm font-semibold text-gray-700">{Math.round(d.v_tool_estimate_4_weeks)} units</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Our forecast (4 weeks)</p>
          <p className="text-sm font-semibold text-gray-700">{Math.round(d.forecast_4_weeks)} units</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Gap</p>
          <p className={`text-sm font-semibold ${gapColor}`}>
            {d.gap_units > 0 ? "+" : ""}{Math.round(d.gap_units)} units ({formatLei(Math.abs(d.gap_lei))} {gapDirection} risk)
          </p>
        </div>
        {d.return_flag && (
          <div className="ml-auto">
            <p className="text-xs text-orange-600 font-medium">
              ⚠ High return rate: {Math.round(d.return_rate * 100)}% — investigate before ordering
            </p>
          </div>
        )}
      </div>
    </Section>
  );
}

function Metric({ label, value, sub, highlight }: { label: string; value: string; sub: string; highlight?: boolean }) {
  return (
    <div className={`rounded-lg p-3 ${highlight ? "bg-blue-50 border border-blue-100" : "bg-gray-50 border border-gray-100"}`}>
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-xl font-bold mt-0.5 ${highlight ? "text-blue-700" : "text-gray-900"}`}>{value}</p>
      <p className="text-xs text-gray-400 mt-0.5">{sub}</p>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <h2 className="text-base font-semibold text-gray-900 mb-4">{title}</h2>
      {children}
    </div>
  );
}
