import type { SkuProfile } from "@/lib/api";
import { formatLei } from "@/lib/format";

const TREND_STYLES: Record<string, string> = {
  GROWING:  "bg-emerald-50 text-emerald-700 border-emerald-200",
  STABLE:   "bg-gray-100 text-gray-600 border-gray-200",
  DECLINING:"bg-red-50 text-red-700 border-red-200",
};

const STATUS_STYLES: Record<string, string> = {
  GREEN:  "bg-emerald-50 text-emerald-700 border-emerald-200",
  YELLOW: "bg-amber-50 text-amber-700 border-amber-200",
  RED:    "bg-red-50 text-red-700 border-red-200",
};

export function SkuHeader({ sku }: { sku: SkuProfile }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wider font-medium mb-1">
            {sku.category} · {sku.sku_id}
          </p>
          <h1 className="text-2xl font-bold text-gray-900">{sku.sku_name}</h1>
          <div className="mt-3 flex flex-wrap gap-2">
            {sku.demand && (
              <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${TREND_STYLES[sku.demand.trend_status]}`}>
                {sku.demand.trend_status}
              </span>
            )}
            {sku.supplier && (
              <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${STATUS_STYLES[sku.supplier.status]}`}>
                Supplier {sku.supplier.status}
              </span>
            )}
            {sku.dead_stock && (
              <span className="px-2.5 py-1 rounded-full text-xs font-semibold border bg-amber-50 text-amber-700 border-amber-200">
                Dead Stock
              </span>
            )}
            {sku.demand?.return_flag && (
              <span className="px-2.5 py-1 rounded-full text-xs font-semibold border bg-orange-50 text-orange-700 border-orange-200">
                High Returns
              </span>
            )}
            {sku.dead_stock?.return_window_urgent && (
              <span className="px-2.5 py-1 rounded-full text-xs font-semibold border bg-red-50 text-red-700 border-red-200">
                Return Window Closing
              </span>
            )}
          </div>
        </div>

        <div className="flex gap-6 text-center">
          <Stat label="Purchase Cost" value={formatLei(sku.purchase_cost_lei)} />
          <Stat label="Selling Price" value={formatLei(sku.selling_price_lei)} />
          <Stat
            label="Gross Margin"
            value={`${Math.round(((sku.selling_price_lei - sku.purchase_cost_lei) / sku.selling_price_lei) * 100)}%`}
          />
          <Stat label="Total Stock" value={`${sku.current_stock} units`} />
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-sm font-semibold text-gray-900 mt-0.5">{value}</p>
    </div>
  );
}
