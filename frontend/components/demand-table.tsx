"use client";

import React, { useState } from "react";
import Link from "next/link";
import { DemandChart } from "@/components/demand-chart";
import { formatLei } from "@/lib/format";
import type { DemandResult } from "@/lib/api";

const TREND_STYLES: Record<string, string> = {
  GROWING: "bg-emerald-50 text-emerald-700",
  STABLE: "bg-gray-100 text-gray-600",
  DECLINING: "bg-red-50 text-red-700",
};

interface DemandTableProps {
  results: DemandResult[];
}

export function DemandTable({ results }: DemandTableProps) {
  const [trendFilter, setTrendFilter] = useState<string>("ALL");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [expandedSku, setExpandedSku] = useState<string | null>(null);

  const categories = Array.from(new Set(results.map((r) => r.category))).sort();

  const filtered = results.filter((r) => {
    if (trendFilter !== "ALL" && r.trend_status !== trendFilter) return false;
    if (categoryFilter !== "ALL" && r.category !== categoryFilter) return false;
    return true;
  });

  function toggleChart(skuId: string) {
    setExpandedSku((prev) => (prev === skuId ? null : skuId));
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-1">
          {["ALL", "GROWING", "STABLE", "DECLINING"].map((t) => (
            <button
              key={t}
              onClick={() => setTrendFilter(t)}
              className={`px-3 py-1 text-xs font-medium rounded-full border transition-colors ${
                trendFilter === t
                  ? "bg-gray-900 text-white border-gray-900"
                  : "bg-white text-gray-500 border-gray-200 hover:border-gray-400"
              }`}
            >
              {t === "ALL" ? "All trends" : t.charAt(0) + t.slice(1).toLowerCase()}
            </button>
          ))}
        </div>

        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="text-xs border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="ALL">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        <span className="text-xs text-gray-400 ml-auto">
          {filtered.length} SKUs · click row to see chart
        </span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                SKU
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Trend
              </th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Real demand/mo
              </th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Forecast 4wk
              </th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Forecast 8wk
              </th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Basic prediction
              </th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Gap (lei)
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <React.Fragment key={r.sku_id}>
                <tr
                  onClick={() => toggleChart(r.sku_id)}
                  className={`border-b border-gray-50 cursor-pointer hover:bg-blue-50 transition-colors ${
                    expandedSku === r.sku_id ? "bg-blue-50" : ""
                  }`}
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/sku/${r.sku_id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="font-medium text-gray-900 text-sm hover:text-blue-700 hover:underline"
                    >
                      {r.sku_name}
                    </Link>
                    <div className="text-xs text-gray-400">{r.category}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${
                        TREND_STYLES[r.trend_status]
                      }`}
                    >
                      {r.trend_status}
                    </span>
                    {r.return_flag && (
                      <span className="ml-1 inline-block px-1.5 py-0.5 rounded text-xs bg-amber-50 text-amber-700 font-medium">
                        High returns
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700 tabular-nums">
                    {Math.round(r.real_demand_monthly)}
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-gray-900 tabular-nums">
                    {Math.round(r.forecast_4_weeks)}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600 tabular-nums">
                    {Math.round(r.forecast_8_weeks)}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500 tabular-nums">
                    {Math.round(r.v_tool_estimate_4_weeks)}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {r.gap_lei > 0 ? (
                      <span className="text-red-600 font-medium">
                        +{formatLei(r.gap_lei)}
                      </span>
                    ) : r.gap_lei < 0 ? (
                      <span className="text-emerald-600 font-medium">
                        {formatLei(r.gap_lei)}
                      </span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                </tr>

                {expandedSku === r.sku_id && (
                  <tr className="bg-blue-50">
                    <td colSpan={7} className="px-6 py-4">
                      <DemandChart
                        skuName={r.sku_name}
                        weeklyHistory={r.weekly_history}
                        forecastWeekly={r.forecast_weekly}
                        trendStatus={r.trend_status}
                      />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-gray-400 text-sm">
                  No SKUs match the current filters
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
