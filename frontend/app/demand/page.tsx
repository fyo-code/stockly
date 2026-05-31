import { apiFetch } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { DemandOverview } from "@/components/demand-overview";
import { DemandTable } from "@/components/demand-table";
import type { ForecastSummary, DemandResponse } from "@/lib/api";

export default async function DemandPage() {
  const [summary, demand] = await Promise.all([
    apiFetch<ForecastSummary>("/api/demand/forecast-summary"),
    apiFetch<DemandResponse>("/api/demand?limit=500"),
  ]);

  if (!summary || !demand) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <p>Cannot reach the backend — make sure uvicorn is running on port 8000.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Demand Forecast</h1>
        <p className="mt-1 text-sm text-gray-500">
          Real demand per SKU — returns stripped, trend detected, 4-week forecast projected.
          Last calculated: {formatDate(summary.calculated_at)}
        </p>
      </div>

      {/* KPI bar */}
      <DemandOverview summary={summary} />

      {/* Explanation callout */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl px-5 py-4">
        <p className="text-sm text-blue-800 font-medium mb-1">How to read this table</p>
        <p className="text-sm text-blue-700">
          <strong>Real demand</strong> strips returns from gross sales — this is what customers
          actually kept. <strong>Forecast 4wk</strong> is our trend-adjusted projection.{" "}
          <strong>Basic prediction</strong> is the method currently in use: take the same month last
          year, divide by days, multiply by 28. It ignores trends, returns, and seasonality shifts.{" "}
          <strong>Gap (lei)</strong> shows how much capital the basic prediction would over- or
          under-order relative to our forecast. Click any row to see the demand chart.
        </p>
      </div>

      {/* Filterable SKU table with expandable charts */}
      <DemandTable results={demand.results} />
    </div>
  );
}
