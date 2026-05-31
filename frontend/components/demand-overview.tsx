import { formatLei } from "@/lib/format";
import type { ForecastSummary } from "@/lib/api";

interface DemandOverviewProps {
  summary: ForecastSummary;
}

export function DemandOverview({ summary }: DemandOverviewProps) {
  const growingPct = Math.round((summary.growing_count / summary.total_skus_analysed) * 100);
  const decliningPct = Math.round((summary.declining_count / summary.total_skus_analysed) * 100);

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <KpiCard
        label="SKUs Analysed"
        value={summary.total_skus_analysed.toLocaleString("ro-RO")}
        sub="with sufficient demand history"
        valueClass="text-gray-900"
      />
      <KpiCard
        label="Growing Demand"
        value={`${summary.growing_count}`}
        sub={`${growingPct}% of SKUs trending up`}
        valueClass="text-emerald-600"
      />
      <KpiCard
        label="Declining Demand"
        value={`${summary.declining_count}`}
        sub={`${decliningPct}% of SKUs trending down`}
        valueClass="text-red-600"
      />
      <KpiCard
        label="Over-Order Risk"
        value={formatLei(summary.total_overorder_risk_lei)}
        sub="if V's estimates used on declining SKUs"
        valueClass="text-amber-600"
      />
    </div>
  );
}

function KpiCard({
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
