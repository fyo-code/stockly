import { apiFetch } from "@/lib/api";
import { ScenarioSimulator } from "@/components/scenario-simulator";
import type { DeadStockResponse } from "@/lib/api";

export default async function ScenarioPage() {
  // Load top dead-stock SKUs as example inputs
  const ds = await apiFetch<DeadStockResponse>("/api/dead-stock?limit=5");
  const examples = (ds?.items ?? [])
    .slice(0, 4)
    .map((item) => ({ sku_id: item.sku_id, sku_name: item.sku_name }))
    // deduplicate by sku_id (items can repeat across stores)
    .filter((v, i, arr) => arr.findIndex((x) => x.sku_id === v.sku_id) === i)
    .slice(0, 3);

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Scenario Simulation</h1>
        <p className="mt-1 text-sm text-gray-500">
          Compare 3 order quantities × 3 demand scenarios before placing an order.
          Runs in real-time against the demand engine and supplier lead times.
        </p>
      </div>

      {/* How it works */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 text-sm">
        <HowItWorksCard
          step="1"
          title="Real demand forecast"
          body="Uses trend-adjusted 8-week forecast, not last year's average."
        />
        <HowItWorksCard
          step="2"
          title="Actual lead times"
          body="Lead time from supplier engine — not the promised days V's tool uses."
        />
        <HowItWorksCard
          step="3"
          title="Budget-aware"
          body="Scenarios that exceed remaining category budget are flagged automatically."
        />
      </div>

      {/* Simulator */}
      <ScenarioSimulator exampleSkuIds={examples} />
    </div>
  );
}

function HowItWorksCard({
  step,
  title,
  body,
}: {
  step: string;
  title: string;
  body: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <div className="flex items-center gap-3 mb-2">
        <span className="w-6 h-6 rounded-full bg-gray-900 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">
          {step}
        </span>
        <p className="font-medium text-gray-900">{title}</p>
      </div>
      <p className="text-gray-500 text-sm">{body}</p>
    </div>
  );
}
