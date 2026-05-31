"use client";

import React, { useState } from "react";
import Link from "next/link";
import { formatLei } from "@/lib/format";
import type { DeadStockItem } from "@/lib/api";

type Trajectory = "ALL" | "SUDDEN_STOP" | "LIFECYCLE_DECLINE" | "NEVER_MOVED";
type WindowFilter = "ALL" | "URGENT" | "OPEN" | "CLOSED";

const TRAJECTORY_LABELS: Record<string, string> = {
  SUDDEN_STOP: "Sudden Stop",
  LIFECYCLE_DECLINE: "Lifecycle Decline",
  NEVER_MOVED: "Never Moved",
};

function windowStatus(item: DeadStockItem): WindowFilter {
  if (item.return_window_urgent) return "URGENT";
  if (item.return_window_open) return "OPEN";
  return "CLOSED";
}

export function DeadStockTable({ items }: { items: DeadStockItem[] }) {
  const [trajectory, setTrajectory] = useState<Trajectory>("ALL");
  const [window_, setWindow] = useState<WindowFilter>("ALL");
  const [sortBy, setSortBy] = useState<"capital" | "days">("capital");
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const filtered = items
    .filter((i) => trajectory === "ALL" || i.trajectory === trajectory)
    .filter((i) => window_ === "ALL" || windowStatus(i) === window_)
    .sort((a, b) =>
      sortBy === "capital"
        ? b.capital_at_risk_lei - a.capital_at_risk_lei
        : b.days_inactive - a.days_inactive
    );

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <FilterGroup
          label="Trajectory"
          options={["ALL", "SUDDEN_STOP", "LIFECYCLE_DECLINE", "NEVER_MOVED"]}
          value={trajectory}
          onChange={(v) => setTrajectory(v as Trajectory)}
          labels={{ ALL: "All", ...TRAJECTORY_LABELS }}
        />
        <div className="w-px h-5 bg-gray-200" />
        <FilterGroup
          label="Return Window"
          options={["ALL", "URGENT", "OPEN", "CLOSED"]}
          value={window_}
          onChange={(v) => setWindow(v as WindowFilter)}
          labels={{ ALL: "All", URGENT: "Urgent", OPEN: "Open", CLOSED: "Closed" }}
        />
        <div className="ml-auto flex items-center gap-2 text-xs text-gray-500">
          <span>Sort:</span>
          <button
            onClick={() => setSortBy("capital")}
            className={`px-2 py-1 rounded ${sortBy === "capital" ? "bg-gray-100 font-medium text-gray-800" : "hover:text-gray-800"}`}
          >
            Capital at Risk
          </button>
          <button
            onClick={() => setSortBy("days")}
            className={`px-2 py-1 rounded ${sortBy === "days" ? "bg-gray-100 font-medium text-gray-800" : "hover:text-gray-800"}`}
          >
            Days Inactive
          </button>
        </div>
        <span className="text-xs text-gray-400">{filtered.length} items</span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-left bg-gray-50">
              <th className="px-5 py-3 text-xs text-gray-500 font-medium">SKU</th>
              <th className="px-5 py-3 text-xs text-gray-500 font-medium">Category</th>
              <th className="px-5 py-3 text-xs text-gray-500 font-medium">Store</th>
              <th className="px-5 py-3 text-xs text-gray-500 font-medium">Days Inactive</th>
              <th className="px-5 py-3 text-xs text-gray-500 font-medium">Units</th>
              <th className="px-5 py-3 text-xs text-gray-500 font-medium">Capital at Risk</th>
              <th className="px-5 py-3 text-xs text-gray-500 font-medium">Trajectory</th>
              <th className="px-5 py-3 text-xs text-gray-500 font-medium">Return Window</th>
              <th className="px-5 py-3 text-xs text-gray-500 font-medium">Budget Unlock</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => {
              const rowKey = `${item.sku_id}-${item.store_id}`;
              const isExpanded = expandedRow === rowKey;
              const ws = windowStatus(item);

              return (
                <React.Fragment key={rowKey}>
                  <tr
                    onClick={() => setExpandedRow(isExpanded ? null : rowKey)}
                    className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer"
                  >
                    <td className="px-5 py-3">
                      <Link
                        href={`/sku/${item.sku_id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="font-medium text-gray-900 hover:text-blue-700 hover:underline"
                      >
                        {item.sku_name}
                      </Link>
                      <p className="text-xs text-gray-400">{item.sku_id}</p>
                    </td>
                    <td className="px-5 py-3 text-xs text-gray-500 capitalize">
                      {item.category}
                    </td>
                    <td className="px-5 py-3 text-xs text-gray-500">{item.store_id}</td>
                    <td className="px-5 py-3">
                      <DaysBadge days={item.days_inactive} />
                    </td>
                    <td className="px-5 py-3 text-gray-700">{item.units_in_stock}</td>
                    <td className="px-5 py-3 font-medium text-gray-900">
                      {formatLei(item.capital_at_risk_lei)}
                    </td>
                    <td className="px-5 py-3 text-xs text-gray-500">
                      {TRAJECTORY_LABELS[item.trajectory] ?? item.trajectory}
                    </td>
                    <td className="px-5 py-3">
                      <WindowBadge status={ws} daysRemaining={item.return_window_days_remaining} />
                    </td>
                    <td className="px-5 py-3 text-sm">
                      {item.budget_unlock_lei > 0 ? (
                        <span className="text-emerald-700 font-medium">
                          {formatLei(item.budget_unlock_lei)}
                        </span>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                  </tr>

                  {/* Expanded detail row */}
                  {isExpanded && (
                    <tr className="bg-amber-50 border-b border-amber-100">
                      <td colSpan={9} className="px-5 py-4">
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
                          <div>
                            <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1">
                              Stock Detail
                            </p>
                            <p className="text-gray-700">
                              {item.units_in_stock} units ×{" "}
                              {formatLei(item.purchase_cost_lei)} cost
                            </p>
                            <p className="text-xs text-gray-500 mt-0.5">
                              Supplier: {item.supplier_id}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1">
                              Return Window
                            </p>
                            {item.return_window_open ? (
                              <p className="text-gray-700">
                                {item.return_window_days_remaining} days remaining
                                {item.return_window_urgent && (
                                  <span className="ml-2 text-red-600 font-medium">Closing soon!</span>
                                )}
                              </p>
                            ) : (
                              <p className="text-gray-500">Window closed — no return possible</p>
                            )}
                          </div>
                          <div>
                            <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1">
                              Recommended Action
                            </p>
                            {item.return_window_urgent ? (
                              <p className="text-red-700 font-medium">
                                Initiate return immediately. Recovers {formatLei(item.budget_unlock_lei)}.
                              </p>
                            ) : item.return_window_open ? (
                              <p className="text-amber-700">
                                Plan return within {item.return_window_days_remaining} days.
                              </p>
                            ) : (
                              <p className="text-gray-600">
                                Consider clearance sale or write-off.
                              </p>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>

        {filtered.length === 0 && (
          <div className="py-12 text-center text-sm text-gray-400">
            No items match the current filters.
          </div>
        )}
      </div>
    </div>
  );
}

// ── Small UI helpers ──────────────────────────────────────────────────────────

function FilterGroup({
  options,
  value,
  onChange,
  labels,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
  labels: Record<string, string>;
}) {
  return (
    <div className="flex gap-1">
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => onChange(opt)}
          className={`px-3 py-1.5 rounded-full text-xs transition-colors ${
            value === opt
              ? "bg-gray-900 text-white"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          {labels[opt] ?? opt}
        </button>
      ))}
    </div>
  );
}

function DaysBadge({ days }: { days: number }) {
  const color =
    days > 180 ? "bg-red-100 text-red-700" : days > 90 ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {days}d
    </span>
  );
}

function WindowBadge({
  status,
  daysRemaining,
}: {
  status: WindowFilter;
  daysRemaining: number;
}) {
  if (status === "URGENT")
    return (
      <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">
        {daysRemaining}d left ⚠
      </span>
    );
  if (status === "OPEN")
    return (
      <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
        {daysRemaining}d left
      </span>
    );
  return (
    <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500">
      Closed
    </span>
  );
}
