import { apiFetch } from "@/lib/api";
import { formatLei, formatDate } from "@/lib/format";
import { QueueList } from "@/components/queue-list";
import type { QueueResponse } from "@/lib/api";

export default async function QueuePage() {
  const [data, explainStatus] = await Promise.all([
    apiFetch<QueueResponse>("/api/queue?limit=600"),
    apiFetch<{ available: boolean }>("/api/explain/status"),
  ]);

  if (!data) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <p>Cannot reach the backend — make sure uvicorn is running on port 8000.</p>
      </div>
    );
  }

  const aiAvailable = explainStatus?.available ?? false;

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Morning Decision Queue</h1>
          <p className="mt-1 text-sm text-gray-500">
            Last calculated: {formatDate(data.calculated_at)}
          </p>
        </div>
        <div className="flex items-center gap-4">
          {/* AI status indicator */}
          <div className="flex items-center gap-2 text-xs">
            <span
              className={`w-2 h-2 rounded-full ${aiAvailable ? "bg-emerald-500" : "bg-gray-300"}`}
            />
            <span className="text-gray-500">
              {aiAvailable ? "AI explanations on" : "AI off — add GEMINI_API_KEY to backend/.env"}
            </span>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-400">Total Financial Impact</p>
            <p className="text-2xl font-bold text-amber-600">
              {formatLei(data.total_financial_impact_lei)}
            </p>
          </div>
        </div>
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <SummaryCard
          label="Urgent"
          value={data.urgent_count}
          sub="immediate action"
          valueClass="text-red-600"
          borderClass="border-l-red-400"
        />
        <SummaryCard
          label="Review"
          value={data.review_count}
          sub="needs attention today"
          valueClass="text-amber-600"
          borderClass="border-l-amber-400"
        />
        <SummaryCard
          label="Info"
          value={data.info_count}
          sub="monitor"
          valueClass="text-gray-600"
          borderClass="border-l-gray-300"
        />
        <SummaryCard
          label="Total Items"
          value={data.total_items}
          sub="across all engines"
          valueClass="text-gray-900"
          borderClass="border-l-gray-200"
        />
      </div>

      {/* Queue list */}
      <QueueList
        items={data.items}
        urgentCount={data.urgent_count}
        reviewCount={data.review_count}
        infoCount={data.info_count}
        aiAvailable={aiAvailable}
      />
    </div>
  );
}

function SummaryCard({
  label,
  value,
  sub,
  valueClass,
  borderClass,
}: {
  label: string;
  value: number;
  sub: string;
  valueClass: string;
  borderClass: string;
}) {
  return (
    <div
      className={`bg-white rounded-xl border border-gray-200 border-l-4 ${borderClass} p-5 shadow-sm`}
    >
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">{label}</p>
      <p className={`mt-2 text-3xl font-bold ${valueClass}`}>{value}</p>
      <p className="mt-1 text-xs text-gray-400">{sub}</p>
    </div>
  );
}
