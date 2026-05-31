import { apiFetch } from "@/lib/api";
import { formatLei, formatDate } from "@/lib/format";
import type { QueueSummary, DeadStockSummary, DemandSummary, DecisionSummary } from "@/lib/api";
import { DecisionSummaryWidget } from "@/components/decision-summary-widget";

async function fetchAll() {
  const [queue, deadStock, demand, decisions] = await Promise.all([
    apiFetch<QueueSummary>("/api/queue/summary"),
    apiFetch<DeadStockSummary>("/api/dead-stock/summary"),
    apiFetch<DemandSummary>("/api/demand/summary"),
    apiFetch<DecisionSummary>("/api/decisions/summary"),
  ]);
  return { queue, deadStock, demand, decisions };
}

export default async function DashboardPage() {
  const { queue, deadStock, demand, decisions } = await fetchAll();

  if (!deadStock) {
    return (
      <div className="flex h-64 items-center justify-center text-gray-400">
        <p>Cannot reach the backend — make sure uvicorn is running on port 8000.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Morning Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Last calculated:{" "}
          {deadStock.calculated_at ? formatDate(deadStock.calculated_at) : "—"}
        </p>
      </div>

      {/* KPI top bar — 3 headline numbers */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* KPI 1: Urgent decisions */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
            Urgent Today
          </p>
          <p className="mt-2 text-4xl font-bold text-red-600">
            {queue ? queue.urgent_count : "—"}
          </p>
          <p className="mt-1 text-sm text-gray-500">items need immediate action</p>
          {queue && (
            <div className="mt-3 flex gap-3 text-xs text-gray-400">
              <span>{queue.review_count} review</span>
              <span>·</span>
              <span>{queue.info_count} info</span>
              <span>·</span>
              <span>{queue.total_items} total</span>
            </div>
          )}
        </div>

        {/* KPI 2: Capital at risk */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
            Capital at Risk
          </p>
          <p className="mt-2 text-4xl font-bold text-amber-600">
            {formatLei(deadStock.total_dead_stock_lei)}
          </p>
          <p className="mt-1 text-sm text-gray-500">dead stock across all stores</p>
          <div className="mt-3 flex gap-3 text-xs text-gray-400">
            <span>{deadStock.sku_count} SKUs affected</span>
            {demand && (
              <>
                <span>·</span>
                <span>{formatLei(demand.total_over_order_risk_lei)} over-order risk</span>
              </>
            )}
          </div>
        </div>

        {/* KPI 3: Budget unlock */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
            Budget Unlock Available
          </p>
          <p className="mt-2 text-4xl font-bold text-emerald-600">
            {formatLei(deadStock.total_budget_unlock_lei)}
          </p>
          <p className="mt-1 text-sm text-gray-500">recoverable via supplier returns</p>
          <div className="mt-3 flex gap-3 text-xs text-gray-400">
            <span>{deadStock.urgent_return_count} windows closing soon</span>
          </div>
        </div>
      </div>

      {/* Secondary stats row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          label="Dead Stock SKUs"
          value={deadStock.sku_count}
          sub="across all stores"
          color="text-gray-900"
        />
        <StatCard
          label="Urgent Return Windows"
          value={deadStock.urgent_return_count}
          sub="< 14 days remaining"
          color="text-red-600"
        />
        <StatCard
          label="Declining SKUs"
          value={demand?.declining ?? 0}
          sub={demand ? `of ${demand.total_skus_analysed} analysed` : "backend loading…"}
          color="text-amber-600"
        />
        <StatCard
          label="Growing SKUs"
          value={demand?.growing ?? 0}
          sub="positive trend"
          color="text-emerald-600"
        />
      </div>

      {/* Quick navigation cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <NavCard
          href="/queue"
          title="Morning Decision Queue"
          description={
            queue
              ? `${queue.urgent_count} urgent · ${queue.review_count} need review`
              : "View all decisions →"
          }
          cta="Open queue →"
          accent="border-l-red-400"
        />
        <NavCard
          href="/dead-stock"
          title="Dead Stock Report"
          description={`${formatLei(deadStock.total_dead_stock_lei)} across ${deadStock.sku_count} SKUs`}
          cta="View dead stock →"
          accent="border-l-amber-400"
        />
        <NavCard
          href="/suppliers"
          title="Supplier Scoreboard"
          description="Reliability scores + stockout risks"
          cta="View suppliers →"
          accent="border-l-blue-400"
        />
      </div>

      {/* Today's decisions */}
      <DecisionSummaryWidget data={decisions} />

      {/* Top offenders preview */}
      {deadStock.top_offenders.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
            <h2 className="text-sm font-semibold text-gray-900">Top Dead Stock Offenders</h2>
            <a href="/dead-stock" className="text-xs text-gray-500 hover:text-gray-800">
              See all {deadStock.sku_count} →
            </a>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left">
                <th className="px-6 py-3 text-xs font-medium text-gray-500">SKU</th>
                <th className="px-6 py-3 text-xs font-medium text-gray-500">Days Inactive</th>
                <th className="px-6 py-3 text-xs font-medium text-gray-500">Capital at Risk</th>
                <th className="px-6 py-3 text-xs font-medium text-gray-500">Trajectory</th>
              </tr>
            </thead>
            <tbody>
              {deadStock.top_offenders.map((item) => (
                <tr key={item.sku_id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-6 py-3">
                    <p className="font-medium text-gray-900">{item.sku_name}</p>
                    <p className="text-xs text-gray-400">{item.sku_id}</p>
                  </td>
                  <td className="px-6 py-3">
                    <span
                      className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${
                        item.days_inactive > 180
                          ? "bg-red-100 text-red-700"
                          : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {item.days_inactive}d
                    </span>
                  </td>
                  <td className="px-6 py-3 font-medium text-gray-900">
                    {formatLei(item.capital_at_risk_lei)}
                  </td>
                  <td className="px-6 py-3 text-xs text-gray-500">
                    {item.trajectory.replace(/_/g, " ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  sub,
  color,
}: {
  label: string;
  value: number;
  sub: string;
  color: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${color}`}>
        {value.toLocaleString("ro-RO")}
      </p>
      <p className="text-xs text-gray-400">{sub}</p>
    </div>
  );
}

function NavCard({
  href,
  title,
  description,
  cta,
  accent,
}: {
  href: string;
  title: string;
  description: string;
  cta: string;
  accent: string;
}) {
  return (
    <a
      href={href}
      className={`block rounded-xl border border-l-4 border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md ${accent}`}
    >
      <p className="text-sm font-medium text-gray-900">{title}</p>
      <p className="mt-1 text-xs text-gray-500">{description}</p>
      <p className="mt-3 text-xs font-medium text-gray-700">{cta}</p>
    </a>
  );
}
