const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Safe fetch — returns null on any error or non-2xx response */
export async function apiFetch<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${BASE_URL}${path}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json() as Promise<T>;
  } catch {
    return null;
  }
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface QueueSummary {
  calculated_at: string;
  total_items: number;
  urgent_count: number;
  review_count: number;
  info_count: number;
  total_financial_impact_lei: number;
}

export interface QueueItem {
  queue_type: string;
  what: string;
  why: string;
  financial_impact_lei: number;
  recommended_action: string;
  status: "URGENT" | "REVIEW" | "INFO";
  sku_id: string | null;
  supplier_id: string | null;
  details: Record<string, unknown>;
}

export interface QueueResponse extends QueueSummary {
  items: QueueItem[];
  showing: number;
}

// Field names match actual API response
export interface DeadStockSummary {
  calculated_at: string;
  total_dead_stock_lei: number;
  total_budget_unlock_lei: number;
  sku_count: number;
  urgent_return_count: number;
  top_offenders: Array<{
    sku_id: string;
    sku_name: string;
    capital_at_risk_lei: number;
    days_inactive: number;
    trajectory: string;
    return_window_urgent: boolean;
  }>;
}

export interface DeadStockItem {
  sku_id: string;
  sku_name: string;
  store_id: string;
  category: string;
  supplier_id: string;
  days_inactive: number;
  units_in_stock: number;
  purchase_cost_lei: number;
  capital_at_risk_lei: number;
  budget_unlock_lei: number;
  dead_stock_score: number;
  trajectory: string;
  return_window_open: boolean;
  return_window_urgent: boolean;
  return_window_days_remaining: number;
}

export interface DeadStockResponse {
  calculated_at: string;
  total_dead_stock_lei: number;
  total_budget_unlock_lei: number;
  sku_count: number;
  urgent_return_count: number;
  total_items: number;
  items: DeadStockItem[];
}

export interface SupplierScore {
  supplier_id: string;
  supplier_name: string;
  status: "GREEN" | "YELLOW" | "RED";
  reliability_score: number;
  order_count: number;
  avg_actual_lead_time_days: number;
  avg_promised_lead_time_days: number;
  lead_time_gap_days: number;
  trend: string;
  stockout_risk_count: number;
}

export interface SupplierDetail extends Omit<SupplierScore, "stockout_risk_count"> {
  delivery_consistency_std: number;
  recent_avg_variance_days: number;
  historical_avg_variance_days: number;
  stockout_risk_skus: Array<{
    sku_id: string;
    sku_name: string;
    message: string;
    days_overdue: number;
    promised_lead_time_days: number;
    actual_lead_time_days: number;
  }>;
}

export interface SupplierResponse {
  calculated_at: string;
  red_count: number;
  yellow_count: number;
  green_count: number;
  total_stockout_risk_skus: number;
  suppliers: SupplierScore[];
}

export interface DemandSummary {
  total_skus_analysed: number;
  growing: number;
  stable: number;
  declining: number;
  high_return_skus: number;
  total_over_order_risk_lei: number;
}

export interface WeeklyHistoryPoint {
  week_ending: string;
  real_demand: number;
  apparent_demand: number;
}

export interface ForecastWeekPoint {
  week_ending: string;
  forecast_demand: number;
}

export interface DemandResult {
  sku_id: string;
  sku_name: string;
  category: string;
  apparent_demand_monthly: number;
  real_demand_monthly: number;
  return_rate: number;
  return_flag: boolean;
  trend_status: "GROWING" | "STABLE" | "DECLINING";
  trend_slope: number;
  forecast_4_weeks: number;
  forecast_8_weeks: number;
  v_tool_estimate_4_weeks: number;
  gap_units: number;
  gap_lei: number;
  weekly_history: WeeklyHistoryPoint[];
  forecast_weekly: ForecastWeekPoint[];
}

export interface DemandResponse {
  calculated_at: string;
  total_skus_analysed: number;
  growing_count: number;
  declining_count: number;
  stable_count: number;
  high_return_count: number;
  total_overorder_risk_lei: number;
  results: DemandResult[];
  total_results: number;
}

export interface ForecastSummary {
  calculated_at: string;
  total_skus_analysed: number;
  growing_count: number;
  stable_count: number;
  declining_count: number;
  high_return_count: number;
  total_overorder_risk_lei: number;
  top_growing_skus: DemandResult[];
  top_declining_skus: DemandResult[];
  top_high_return_skus: DemandResult[];
}

export interface ScenarioOutcome {
  order_qty: number;
  order_cost_lei: number;
  projected_units_sold: number;
  projected_revenue_lei: number;
  projected_unsold_units: number;
  projected_dead_stock_lei: number;
  projected_shortage_units: number;
  projected_lost_revenue_lei: number;
  projected_margin_lei: number;
  projected_margin_pct: number;
  within_budget: boolean;
  budget_remaining_after_lei: number | null;
}

export interface SensitivityRange {
  low_demand: ScenarioOutcome;
  base_demand: ScenarioOutcome;
  high_demand: ScenarioOutcome;
}

export interface ExplainResponse {
  explanation: string | null;
  source: "gemini" | "unavailable";
}

export interface SkuProfile {
  sku_id: string;
  sku_name: string;
  category: string;
  purchase_cost_lei: number;
  selling_price_lei: number;
  current_stock: number;
  store_breakdown: Array<{ store_id: string; units_in_stock: number }>;
  coverage: {
    weeks_of_coverage: number;
    lead_time_weeks: number;
    reorder_needed: boolean;
  } | null;
  demand: (DemandResult & { weekly_history: WeeklyHistoryPoint[]; forecast_weekly: ForecastWeekPoint[] }) | null;
  supplier: {
    supplier_id: string;
    supplier_name: string;
    reliability_score: number;
    status: "GREEN" | "YELLOW" | "RED";
    avg_promised_lead_time_days: number;
    avg_actual_lead_time_days: number;
    lead_time_gap_days: number;
    trend: string;
    stockout_risk: {
      sku_id: string;
      sku_name: string;
      promised_lead_time_days: number;
      actual_lead_time_days: number;
      days_overdue: number;
      message: string;
    } | null;
  } | null;
  dead_stock: {
    is_dead_stock: boolean;
    days_inactive: number;
    total_capital_at_risk_lei: number;
    total_budget_unlock_lei: number;
    trajectory: string;
    return_window_open: boolean;
    return_window_urgent: boolean;
    return_window_days_remaining: number | null;
    store_breakdown: Array<{
      store_id: string;
      days_inactive: number;
      units_in_stock: number;
      capital_at_risk_lei: number;
      return_window_open: boolean;
    }>;
  } | null;
}

export interface DecisionSummary {
  today_only: boolean;
  total: number;
  approved: number;
  skipped: number;
  overridden: number;
  approved_impact_lei: number;
  skipped_impact_lei: number;
  overridden_impact_lei: number;
  by_queue_type: Array<{ queue_type: string; count: number; impact_lei: number }>;
  recent: Array<{
    id: number;
    sku_id: string;
    queue_type: string;
    action: string;
    override_qty: number | null;
    financial_impact_lei: number | null;
    decided_at: string;
  }>;
}

export interface ScenarioResult {
  sku_id: string;
  sku_name: string;
  category: string;
  current_stock: number;
  weekly_real_demand: number;
  forecast_8_weeks: number;
  selling_price_lei: number;
  purchase_cost_lei: number;
  real_lead_time_weeks: number;
  recommended_qty: number;
  budget_lei: number | null;
  budget_remaining_lei: number | null;
  scenarios: {
    conservative: SensitivityRange;
    base: SensitivityRange;
    aggressive: SensitivityRange;
  };
}
