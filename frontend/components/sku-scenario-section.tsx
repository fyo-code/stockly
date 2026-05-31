"use client";

import { useState, useTransition } from "react";
import { formatLei } from "@/lib/format";
import type { ScenarioResult, ScenarioOutcome } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const SCENARIO_LABELS: Record<string, string> = {
  conservative: "Conservative (−20%)",
  base:          "Base (recommended)",
  aggressive:    "Aggressive (+20%)",
};

const DEMAND_LABELS: Record<string, string> = {
  low_demand:  "Low −20%",
  base_demand: "Expected",
  high_demand: "High +20%",
};

type ScenarioKey = "conservative" | "base" | "aggressive";
type DemandKey   = "low_demand" | "base_demand" | "high_demand";
const SCENARIO_KEYS: ScenarioKey[] = ["conservative", "base", "aggressive"];
const DEMAND_KEYS:   DemandKey[]   = ["low_demand", "base_demand", "high_demand"];

export function SkuScenarioSection({ skuId }: { skuId: string }) {
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [ran, setRan] = useState(false);

  function run() {
    setError(null);
    setRan(true);
    startTransition(async () => {
      try {
        const res = await fetch(`${API}/api/scenario/${skuId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          setError(body.detail ?? `Error ${res.status}`);
          return;
        }
        setResult(await res.json());
      } catch {
        setError("Cannot reach the backend.");
      }
    });
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-900">Scenario Simulation</h2>
        {!ran && (
          <button
            onClick={run}
            className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-700 transition-colors"
          >
            Run Simulation
          </button>
        )}
      </div>

      {!ran && (
        <p className="text-sm text-gray-400">
          Compare 3 order quantities × 3 demand scenarios to see financial outcomes before committing.
        </p>
      )}

      {isPending && (
        <div className="flex items-center gap-2 text-sm text-gray-400 py-6">
          <span className="animate-spin">⟳</span> Calculating scenarios…
        </div>
      )}

      {error && <p className="text-sm text-red-600 mt-2">{error}</p>}

      {result && !isPending && <ScenarioGrid result={result} onRerun={run} />}
    </div>
  );
}

function ScenarioGrid({ result: r, onRerun }: { result: ScenarioResult; onRerun: () => void }) {
  return (
    <div className="space-y-4">
      {/* Summary row */}
      <div className="flex flex-wrap gap-4 text-sm">
        <span className="text-gray-500">
          Stock: <strong className="text-gray-900">{r.current_stock} units</strong>
        </span>
        <span className="text-gray-500">
          8-week forecast: <strong className="text-gray-900">{Math.round(r.forecast_8_weeks)} units</strong>
        </span>
        <span className="text-gray-500">
          Recommended: <strong className="text-blue-700">{r.recommended_qty} units ({formatLei(r.recommended_qty * r.purchase_cost_lei)})</strong>
        </span>
        <button onClick={onRerun} className="ml-auto text-xs text-gray-400 hover:text-gray-600 underline">
          Recalculate
        </button>
      </div>

      {/* 3×3 grid */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="w-36 pb-2" />
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
          <tbody>
            {SCENARIO_KEYS.map((sk) => (
              <tr key={sk}>
                <td className="pr-3 pb-3 align-top">
                  <div className={`text-xs font-medium pt-4 ${sk === "base" ? "text-blue-700" : "text-gray-500"}`}>
                    {SCENARIO_LABELS[sk]}
                  </div>
                </td>
                {DEMAND_KEYS.map((dk) => {
                  const outcome = r.scenarios[sk][dk];
                  return (
                    <td key={dk} className="pb-3 px-2 align-top">
                      <Cell outcome={outcome} isRecommended={sk === "base" && dk === "base_demand"} purchaseCost={r.purchase_cost_lei} />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Cell({ outcome: o, isRecommended, purchaseCost }: { outcome: ScenarioOutcome; isRecommended: boolean; purchaseCost: number }) {
  const marginPct = Math.round(o.projected_margin_pct * 100);
  const hasDeadStock = o.projected_unsold_units > 0;
  const hasShortage = o.projected_shortage_units > 0;

  let bg = "bg-white border-gray-200";
  if (isRecommended) bg = "bg-blue-50 border-blue-300";
  else if (!o.within_budget) bg = "bg-gray-50 border-gray-200";
  else if (hasDeadStock && o.projected_dead_stock_lei > o.order_cost_lei * 0.2) bg = "bg-amber-50 border-amber-200";
  else if (hasShortage && o.projected_lost_revenue_lei > o.projected_revenue_lei * 0.15) bg = "bg-red-50 border-red-200";
  else if (marginPct >= 65) bg = "bg-emerald-50 border-emerald-200";

  return (
    <div className={`rounded-xl border ${bg} p-3 min-w-[140px] ${!o.within_budget ? "opacity-60" : ""}`}>
      {isRecommended && <p className="text-xs font-semibold text-blue-700 mb-1">★ Recommended</p>}
      <p className="text-base font-bold text-gray-900">{o.order_qty} units</p>
      <p className="text-xs text-gray-500">{formatLei(o.order_cost_lei)}</p>
      <p className={`mt-1.5 text-sm font-semibold ${marginPct >= 65 ? "text-emerald-700" : marginPct >= 50 ? "text-gray-700" : "text-red-600"}`}>
        {marginPct}%
      </p>
      {hasDeadStock && <p className="mt-1 text-xs text-amber-700">⚠ {o.projected_unsold_units} unsold</p>}
      {hasShortage && <p className="mt-1 text-xs text-red-600">📦 {o.projected_shortage_units} short</p>}
      {!o.within_budget && <p className="mt-1 text-xs text-gray-400">✗ Over budget</p>}
    </div>
  );
}
