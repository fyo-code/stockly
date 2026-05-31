"use client";

import { useState } from "react";
import Link from "next/link";
import type { SupplierScore, SupplierDetail } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const STATUS_CONFIG = {
  RED:    { label: "RED",    bg: "bg-red-100",    text: "text-red-700",    bar: "bg-red-500"    },
  YELLOW: { label: "YELLOW", bg: "bg-amber-100",  text: "text-amber-700",  bar: "bg-amber-500"  },
  GREEN:  { label: "GREEN",  bg: "bg-emerald-100",text: "text-emerald-700",bar: "bg-emerald-500" },
};

export function SupplierScoreboard({ suppliers }: { suppliers: SupplierScore[] }) {
  return (
    <div className="space-y-4">
      {suppliers.map((s) => (
        <SupplierCard key={s.supplier_id} supplier={s} />
      ))}
    </div>
  );
}

function SupplierCard({ supplier: s }: { supplier: SupplierScore }) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState<SupplierDetail | null>(null);
  const [loading, setLoading] = useState(false);

  const cfg = STATUS_CONFIG[s.status];

  async function toggle() {
    if (!expanded && !detail) {
      setLoading(true);
      try {
        const res = await fetch(`${API}/api/suppliers/${s.supplier_id}`);
        if (res.ok) setDetail(await res.json());
      } finally {
        setLoading(false);
      }
    }
    setExpanded((prev) => !prev);
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Main card row */}
      <div className="px-6 py-5">
        <div className="flex items-start justify-between gap-4">
          {/* Left: name + status */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h3 className="font-semibold text-gray-900">{s.supplier_name}</h3>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}
              >
                {cfg.label}
              </span>
              <span className="text-xs text-gray-400">{s.supplier_id}</span>
            </div>

            {/* Score bar */}
            <div className="mt-3 flex items-center gap-3">
              <div className="flex-1 max-w-xs bg-gray-100 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${cfg.bar} transition-all`}
                  style={{ width: `${s.reliability_score}%` }}
                />
              </div>
              <span className="text-sm font-bold text-gray-900">
                {s.reliability_score.toFixed(0)}/100
              </span>
            </div>
          </div>

          {/* Right: lead time stats */}
          <div className="flex gap-6 text-center flex-shrink-0">
            <Stat
              label="Promised"
              value={`${s.avg_promised_lead_time_days.toFixed(0)}d`}
              valueClass="text-gray-700"
            />
            <Stat
              label="Actual"
              value={`${s.avg_actual_lead_time_days.toFixed(0)}d`}
              valueClass={s.lead_time_gap_days > 5 ? "text-red-600 font-bold" : "text-gray-700"}
            />
            <Stat
              label="Gap"
              value={`+${s.lead_time_gap_days.toFixed(0)}d`}
              valueClass={s.lead_time_gap_days > 5 ? "text-red-600 font-bold" : "text-emerald-600"}
            />
            <Stat
              label="Orders"
              value={s.order_count.toString()}
              valueClass="text-gray-700"
            />
          </div>
        </div>

        {/* V's tool callout for YELLOW/RED */}
        {s.lead_time_gap_days > 5 && (
          <div className="mt-3 rounded-lg bg-red-50 border border-red-100 px-4 py-2 text-xs text-red-700">
            <span className="font-semibold">V&apos;s tool risk:</span> calculates reorder using{" "}
            {s.avg_promised_lead_time_days.toFixed(0)}-day lead time. Actual average is{" "}
            {s.avg_actual_lead_time_days.toFixed(0)} days.{" "}
            <span className="font-semibold">
              {s.stockout_risk_count} SKUs would be ordered {s.lead_time_gap_days.toFixed(0)} days too late.
            </span>
          </div>
        )}

        {/* Expand button */}
        <div className="mt-3 flex items-center justify-between">
          <div className="flex gap-4 text-xs text-gray-500">
            <span>Trend: <span className="font-medium text-gray-700">{s.trend}</span></span>
            {s.stockout_risk_count > 0 && (
              <span className="text-red-600 font-medium">
                {s.stockout_risk_count} SKUs at stockout risk
              </span>
            )}
          </div>
          {s.stockout_risk_count > 0 && (
            <button
              onClick={toggle}
              className="text-xs text-gray-500 hover:text-gray-900 flex items-center gap-1"
            >
              {loading ? "Loading…" : expanded ? "Hide SKUs ↑" : `Show ${s.stockout_risk_count} at-risk SKUs ↓`}
            </button>
          )}
        </div>
      </div>

      {/* Expanded stockout SKU list */}
      {expanded && detail && (
        <div className="border-t border-gray-100 bg-gray-50">
          <div className="px-6 py-3 text-xs text-gray-500 font-medium uppercase tracking-wider border-b border-gray-100">
            Stockout Risk SKUs — order {detail.lead_time_gap_days.toFixed(0)} days earlier than V&apos;s tool suggests
          </div>
          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-gray-100">
                  <th className="px-6 py-2 text-xs text-gray-500 font-medium">SKU</th>
                  <th className="px-6 py-2 text-xs text-gray-500 font-medium">Promised Lead Time</th>
                  <th className="px-6 py-2 text-xs text-gray-500 font-medium">Actual Lead Time</th>
                  <th className="px-6 py-2 text-xs text-gray-500 font-medium">Days Overdue</th>
                </tr>
              </thead>
              <tbody>
                {detail.stockout_risk_skus.map((sku) => (
                  <tr key={sku.sku_id} className="border-b border-gray-50 hover:bg-white">
                    <td className="px-6 py-2">
                      <Link
                        href={`/sku/${sku.sku_id}`}
                        className="font-medium text-gray-800 hover:text-blue-700 hover:underline"
                      >
                        {sku.sku_name}
                      </Link>
                      <p className="text-xs text-gray-400">{sku.sku_id}</p>
                    </td>
                    <td className="px-6 py-2 text-gray-600">{sku.promised_lead_time_days.toFixed(0)}d</td>
                    <td className="px-6 py-2 text-red-600 font-medium">{sku.actual_lead_time_days.toFixed(0)}d</td>
                    <td className="px-6 py-2">
                      <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">
                        +{sku.days_overdue.toFixed(0)}d
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  valueClass,
}: {
  label: string;
  value: string;
  valueClass: string;
}) {
  return (
    <div>
      <p className="text-xs text-gray-400">{label}</p>
      <p className={`text-lg font-semibold ${valueClass}`}>{value}</p>
    </div>
  );
}
