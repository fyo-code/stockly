import { apiFetch } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { SupplierScoreboard } from "@/components/supplier-scoreboard";
import type { SupplierResponse } from "@/lib/api";

export default async function SuppliersPage() {
  const data = await apiFetch<SupplierResponse>("/api/suppliers");

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
        <h1 className="text-2xl font-semibold text-gray-900">Supplier Scoreboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Last calculated: {formatDate(data.calculated_at)}
        </p>
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <SummaryCard
          label="RED — Critical"
          value={data.red_count}
          sub="immediate action needed"
          valueClass="text-red-600"
          bgClass="border-l-red-400"
        />
        <SummaryCard
          label="YELLOW — At Risk"
          value={data.yellow_count}
          sub="chronically late suppliers"
          valueClass="text-amber-600"
          bgClass="border-l-amber-400"
        />
        <SummaryCard
          label="GREEN — Reliable"
          value={data.green_count}
          sub="on time, consistent"
          valueClass="text-emerald-600"
          bgClass="border-l-emerald-400"
        />
        <SummaryCard
          label="SKUs at Stockout Risk"
          value={data.total_stockout_risk_skus}
          sub="V's tool would order too late"
          valueClass="text-red-600"
          bgClass="border-l-red-300"
        />
      </div>

      {/* Insight banner for YELLOW suppliers */}
      {data.yellow_count > 0 && (
        <div className="rounded-xl bg-amber-50 border border-amber-200 px-6 py-4">
          <p className="text-sm font-semibold text-amber-800">
            {data.yellow_count} Italian suppliers are running ~14 days late on average
          </p>
          <p className="mt-1 text-sm text-amber-700">
            V&apos;s tool uses the promised lead time (22 days). The actual average is 36 days.
            Orders placed using V&apos;s reorder trigger will arrive 14 days late —
            causing stockouts on {data.total_stockout_risk_skus} SKUs.
          </p>
        </div>
      )}

      {/* Scoreboard */}
      <SupplierScoreboard suppliers={data.suppliers} />
    </div>
  );
}

function SummaryCard({
  label,
  value,
  sub,
  valueClass,
  bgClass,
}: {
  label: string;
  value: number;
  sub: string;
  valueClass: string;
  bgClass: string;
}) {
  return (
    <div
      className={`bg-white rounded-xl border border-gray-200 border-l-4 ${bgClass} p-5 shadow-sm`}
    >
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">{label}</p>
      <p className={`mt-2 text-3xl font-bold ${valueClass}`}>{value}</p>
      <p className="mt-1 text-xs text-gray-400">{sub}</p>
    </div>
  );
}
