"use client";

import { useState, useTransition } from "react";
import { formatLei } from "@/lib/format";
import type { ScenarioResult, ScenarioOutcome } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const SCENARIO_LABELS: Record<string, string> = {
  conservative: "Conservative  (−20% order)",
  base:          "Base  (recommended)",
  aggressive:    "Aggressive  (+20% order)",
};

const DEMAND_LABELS: Record<string, string> = {
  low_demand:  "Low Demand −20%",
  base_demand: "Expected",
  high_demand: "High Demand +20%",
};

type ScenarioKey = "conservative" | "base" | "aggressive";
type DemandKey   = "low_demand"   | "base_demand" | "high_demand";

const SCENARIO_KEYS: ScenarioKey[] = ["conservative", "base", "aggressive"];
const DEMAND_KEYS:   DemandKey[]   = ["low_demand", "base_demand", "high_demand"];

export function ScenarioSimulator({
  exampleSkuIds,
}: {
  exampleSkuIds: Array<{ sku_id: string; sku_name: string }>;
}) {
  const [skuId, setSkuId] = useState(exampleSkuIds[0]?.sku_id ?? "");
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function runScenario(id = skuId) {
    if (!id.trim()) return;
    setError(null);
    startTransition(async () => {
      try {
        const res = await fetch(`${API}/api/scenario/${id.trim()}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          setError(body.detail ?? `Error ${res.status}`);
          setResult(null);
          return;
        }
        setResult(await res.json());
      } catch {
        setError("Cannot reach the backend.");
        setResult(null);
      }
    });
  }

  return (
    <div className="space-y-6">
      {/* Search form */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          SKU ID
        </label>
        <div className="flex gap-3">
          <input
            type="text"
            value={skuId}
            onChange={(e) => setSkuId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runScenario()}
            placeholder="e.g. SKU0001"
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
          />
          <button
            onClick={() => runScenario()}
            disabled={isPending || !skuId.trim()}
            className="px-5 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-40 transition-colors"
          >
            {isPending ? "Running…" : "Run Simulation"}
          </button>
        </div>

        {/* Example SKUs */}
        {exampleSkuIds.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2 items-center">
            <span className="text-xs text-gray-400">Try:</span>
            {exampleSkuIds.map((s) => (
              <button
                key={s.sku_id}
                onClick={() => { setSkuId(s.sku_id); runScenario(s.sku_id); }}
                className="px-3 py-1 rounded-full bg-gray-100 text-xs text-gray-700 hover:bg-gray-200 transition-colors"
              >
                {s.sku_name} ({s.sku_id})
              </button>
            ))}
          </div>
        )}

        {error && (
          <p className="mt-3 text-sm text-red-600">{error}</p>
        )}
      </div>

      {/* Result */}
      {result && <ScenarioOutput result={result} />}
    </div>
  );
}

// ── Scenario output ───────────────────────────────────────────────────────────

function ScenarioOutput({ result: r }: { result: ScenarioResult }) {
  return (
    <div className="space-y-6">
      {/* SKU header */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{r.sku_name}</h2>
            <p className="text-sm text-gray-500">
              {r.sku_id} · {r.category}
            </p>
          </div>
          <div className="flex gap-6 text-center">
            <Metric label="Current Stock"   value={`${r.current_stock} units`} />
            <Metric label="Weekly Demand"   value={`${r.weekly_real_demand} units`} />
            <Metric label="8-Week Forecast" value={`${r.forecast_8_weeks.toFixed(0)} units`} />
            <Metric label="Supplier Lead"   value={`${r.real_lead_time_weeks.toFixed(1)} weeks`} />
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-4">
          <div className="flex items-center gap-2 rounded-lg bg-blue-50 border border-blue-100 px-4 py-2.5">
            <span className="text-sm text-blue-800">
              <span className="font-semibold">Recommended order:</span>{" "}
              {r.recommended_qty} units at {formatLei(r.recommended_qty * r.purchase_cost_lei)}
            </span>
          </div>
          {r.budget_remaining_lei != null && (
            <div
              className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm ${
                r.budget_remaining_lei > r.recommended_qty * r.purchase_cost_lei
                  ? "bg-emerald-50 border-emerald-100 text-emerald-800"
                  : "bg-red-50 border-red-100 text-red-800"
              }`}
            >
              <span className="font-semibold">Budget remaining:</span>{" "}
              {formatLei(r.budget_remaining_lei)}
            </div>
          )}
        </div>
      </div>

      {/* 3×3 scenario grid */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          Order Scenarios × Demand Sensitivity
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="w-44 pb-2" />
                {DEMAND_KEYS.map((dk) => (
                  <th
                    key={dk}
                    className={`pb-2 px-2 text-center text-xs font-semibold ${
                      dk === "base_demand" ? "text-blue-700" : "text-gray-500"
                    }`}
                  >
                    {DEMAND_LABELS[dk]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="space-y-2">
              {SCENARIO_KEYS.map((sk) => (
                <tr key={sk}>
                  <td className="pr-3 pb-3 align-top">
                    <div
                      className={`text-xs font-medium pt-4 ${
                        sk === "base" ? "text-blue-700" : "text-gray-500"
                      }`}
                    >
                      {SCENARIO_LABELS[sk]}
                    </div>
                  </td>
                  {DEMAND_KEYS.map((dk) => {
                    const outcome = r.scenarios[sk][dk];
                    const isRecommended = sk === "base" && dk === "base_demand";
                    return (
                      <td key={dk} className="pb-3 px-2 align-top">
                        <ScenarioCell
                          outcome={outcome}
                          isRecommended={isRecommended}
                          purchaseCost={r.purchase_cost_lei}
                        />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-emerald-100 border border-emerald-200" />
          High margin (&gt;65%)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-amber-50 border border-amber-200" />
          Dead stock risk (unsold units)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-red-50 border border-red-200" />
          Shortage risk (lost revenue)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-blue-50 border border-blue-200" />
          Recommended scenario
        </span>
      </div>
    </div>
  );
}

// ── Single scenario cell ──────────────────────────────────────────────────────

function ScenarioCell({
  outcome: o,
  isRecommended,
  purchaseCost,
}: {
  outcome: ScenarioOutcome;
  isRecommended: boolean;
  purchaseCost: number;
}) {
  const marginPct = Math.round(o.projected_margin_pct * 100);
  const hasDeadStock = o.projected_unsold_units > 0;
  const hasShortage = o.projected_shortage_units > 0;

  let cellBg = "bg-white";
  let cellBorder = "border-gray-200";

  if (isRecommended) {
    cellBg = "bg-blue-50";
    cellBorder = "border-blue-300";
  } else if (!o.within_budget) {
    cellBg = "bg-gray-50";
    cellBorder = "border-gray-200";
  } else if (hasDeadStock && o.projected_dead_stock_lei > o.order_cost_lei * 0.2) {
    cellBg = "bg-amber-50";
    cellBorder = "border-amber-200";
  } else if (hasShortage && o.projected_lost_revenue_lei > o.projected_revenue_lei * 0.15) {
    cellBg = "bg-red-50";
    cellBorder = "border-red-200";
  } else if (marginPct >= 65) {
    cellBg = "bg-emerald-50";
    cellBorder = "border-emerald-200";
  }

  return (
    <div
      className={`rounded-xl border ${cellBorder} ${cellBg} p-4 min-w-[160px] ${
        !o.within_budget ? "opacity-60" : ""
      }`}
    >
      {isRecommended && (
        <p className="text-xs font-semibold text-blue-700 mb-2">★ Recommended</p>
      )}

      {/* Order */}
      <p className="text-lg font-bold text-gray-900">{o.order_qty} units</p>
      <p className="text-xs text-gray-500">{formatLei(o.order_cost_lei)} cost</p>

      {/* Margin */}
      <div className="mt-2">
        <span
          className={`text-sm font-semibold ${
            marginPct >= 65
              ? "text-emerald-700"
              : marginPct >= 50
              ? "text-gray-700"
              : "text-red-600"
          }`}
        >
          {marginPct}% margin
        </span>
        <span className="ml-1 text-xs text-gray-400">
          ({formatLei(o.projected_margin_lei)})
        </span>
      </div>

      {/* Risks */}
      {hasDeadStock && (
        <p className="mt-1.5 text-xs text-amber-700">
          ⚠ {o.projected_unsold_units} units unsold ({formatLei(o.projected_dead_stock_lei)})
        </p>
      )}
      {hasShortage && (
        <p className="mt-1.5 text-xs text-red-600">
          📦 {o.projected_shortage_units} short ({formatLei(o.projected_lost_revenue_lei)} lost)
        </p>
      )}

      {/* Budget */}
      {!o.within_budget && (
        <p className="mt-1.5 text-xs font-medium text-gray-400">✗ Over budget</p>
      )}
      {o.within_budget && o.budget_remaining_after_lei != null && (
        <p className="mt-1.5 text-xs text-gray-400">
          {formatLei(o.budget_remaining_after_lei)} left
        </p>
      )}
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-sm font-semibold text-gray-900">{value}</p>
    </div>
  );
}
