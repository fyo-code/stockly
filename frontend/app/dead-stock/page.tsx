import { apiFetch } from "@/lib/api";
import { formatLei, formatDate } from "@/lib/format";
import { DeadStockTable } from "@/components/dead-stock-table";
import type { DeadStockResponse } from "@/lib/api";

export default async function DeadStockPage() {
  const data = await apiFetch<DeadStockResponse>("/api/dead-stock");

  if (!data) {
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
        <h1 className="text-2xl font-semibold text-gray-900">Dead Stock Report</h1>
        <p className="mt-1 text-sm text-gray-500">
          Last calculated: {formatDate(data.calculated_at)}
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <SummaryCard
          label="Total Dead Stock"
          value={formatLei(data.total_dead_stock_lei)}
          sub="capital locked in unsold inventory"
          valueClass="text-amber-600"
        />
        <SummaryCard
          label="SKUs Affected"
          value={data.sku_count.toString()}
          sub={`${data.total_items} store-level records`}
          valueClass="text-gray-900"
        />
        <SummaryCard
          label="Urgent Return Windows"
          value={data.urgent_return_count.toString()}
          sub="windows close in < 14 days"
          valueClass="text-red-600"
        />
        <SummaryCard
          label="Budget Unlock Available"
          value={formatLei(data.total_budget_unlock_lei)}
          sub="recoverable via supplier returns"
          valueClass="text-emerald-600"
        />
      </div>

      {/* Filterable table */}
      <DeadStockTable items={data.items} />
    </div>
  );
}

function SummaryCard({
  label,
  value,
  sub,
  valueClass,
}: {
  label: string;
  value: string;
  sub: string;
  valueClass: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">{label}</p>
      <p className={`mt-2 text-2xl font-bold ${valueClass}`}>{value}</p>
      <p className="mt-1 text-xs text-gray-400">{sub}</p>
    </div>
  );
}
