"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { WeeklyHistoryPoint, ForecastWeekPoint } from "@/lib/api";

interface DemandChartProps {
  skuName: string;
  weeklyHistory: WeeklyHistoryPoint[];
  forecastWeekly: ForecastWeekPoint[];
  trendStatus: "GROWING" | "STABLE" | "DECLINING";
}

function formatWeekLabel(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

export function DemandChart({
  skuName,
  weeklyHistory,
  forecastWeekly,
  trendStatus,
}: DemandChartProps) {
  if (weeklyHistory.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-400 text-sm">
        Insufficient data for chart
      </div>
    );
  }

  // Merge history and forecast into one continuous series for the chart.
  // History points have real_demand + apparent_demand.
  // Forecast points have forecast_demand only.
  // The last history point date is used as the "today" divider.
  const historyPoints = weeklyHistory.map((p) => ({
    week: formatWeekLabel(p.week_ending),
    real_demand: p.real_demand,
    apparent_demand: p.apparent_demand,
    forecast_demand: undefined as number | undefined,
    isForecast: false,
  }));

  const forecastPoints = forecastWeekly.map((p) => ({
    week: formatWeekLabel(p.week_ending),
    real_demand: undefined as number | undefined,
    apparent_demand: undefined as number | undefined,
    forecast_demand: p.forecast_demand,
    isForecast: true,
  }));

  // Connect history to forecast with a bridge point (last history real demand as forecast start)
  const lastHistory = historyPoints[historyPoints.length - 1];
  const bridge = {
    week: lastHistory.week,
    real_demand: undefined as number | undefined,
    apparent_demand: undefined as number | undefined,
    forecast_demand: lastHistory.real_demand,
    isForecast: true,
  };

  const data = [...historyPoints, bridge, ...forecastPoints];
  const todayLabel = lastHistory.week;

  const trendColor =
    trendStatus === "GROWING"
      ? "#10b981"
      : trendStatus === "DECLINING"
      ? "#ef4444"
      : "#6b7280";

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-700 truncate">{skuName}</p>
        <span
          className="text-xs font-semibold px-2 py-0.5 rounded-full"
          style={{
            color: trendColor,
            backgroundColor: `${trendColor}18`,
          }}
        >
          {trendStatus}
        </span>
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="week"
            tick={{ fontSize: 11, fill: "#9ca3af" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#9ca3af" }}
            tickLine={false}
            axisLine={false}
            width={36}
          />
          <Tooltip
            contentStyle={{
              fontSize: 12,
              borderRadius: 8,
              border: "1px solid #e5e7eb",
              boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
            }}
            formatter={(value, name) => {
              const labels: Record<string, string> = {
                real_demand: "Real demand",
                apparent_demand: "Apparent (gross)",
                forecast_demand: "Forecast",
              };
              const key = String(name ?? "");
              return [Math.round(Number(value ?? 0)), labels[key] ?? key];
            }}
          />
          <Legend
            iconType="line"
            wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
            formatter={(value: string) => {
              const labels: Record<string, string> = {
                real_demand: "Real demand (returns stripped)",
                apparent_demand: "Apparent demand (gross)",
                forecast_demand: "Forecast (next 4 weeks)",
              };
              return labels[value] ?? value;
            }}
          />
          <ReferenceLine
            x={todayLabel}
            stroke="#d1d5db"
            strokeDasharray="4 4"
            label={{ value: "Today", position: "top", fontSize: 10, fill: "#9ca3af" }}
          />
          <Line
            type="monotone"
            dataKey="real_demand"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ r: 3, fill: "#3b82f6" }}
            activeDot={{ r: 5 }}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="apparent_demand"
            stroke="#93c5fd"
            strokeWidth={1.5}
            strokeDasharray="5 3"
            dot={false}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="forecast_demand"
            stroke={trendColor}
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={{ r: 3, fill: trendColor }}
            activeDot={{ r: 5 }}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>

      <p className="text-xs text-gray-400">
        Solid blue = real demand (returns stripped) · Dashed blue = apparent (gross) ·
        Dashed {trendStatus === "GROWING" ? "green" : trendStatus === "DECLINING" ? "red" : "grey"} = forecast
      </p>
    </div>
  );
}
