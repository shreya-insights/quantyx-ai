import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import type { LTVSegmentsResponse } from "@/types/api.types";
import { formatCurrency, formatNumber } from "@/utils/format";
import { useChartColors } from "@/hooks/useChartColors";

const SEGMENT_COLOR: Record<string, string> = {
  high: "#10b981",
  medium: "#3b82f6",
  low: "#f59e0b",
};

interface Props {
  data: LTVSegmentsResponse;
}

export function LTVSegmentChart({ data }: Props) {
  const c = useChartColors();
  const chartData = data.segments.map((s) => ({
    name: s.segment.charAt(0).toUpperCase() + s.segment.slice(1),
    value: s.user_count,
    avgSpend: s.avg_spend,
    pct: s.pct_of_total,
    key: s.segment,
  }));

  const tooltipStyle = {
    borderRadius: 8,
    border: `1px solid ${c.tooltipBorder}`,
    backgroundColor: c.tooltipBg,
    fontSize: 12,
  };

  return (
    <div className="space-y-4">
      <ResponsiveContainer minWidth={0} width="100%" height={280}>
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={72}
            outerRadius={112}
            paddingAngle={2}
            isAnimationActive
            animationDuration={700}
          >
            {chartData.map((entry) => (
              <Cell key={entry.key} fill={SEGMENT_COLOR[entry.key] ?? "#64748b"} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value, _name, item) => {
              const v = typeof value === "number" ? value : Number(value);
              const p = item?.payload as { avgSpend?: number; pct?: number } | undefined;
              return [
                `${formatNumber(v)} users (${p?.pct ?? 0}%) · avg ${formatCurrency(p?.avgSpend ?? 0)}`,
                "",
              ];
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      <ul className="flex flex-wrap gap-4 justify-center text-xs text-slate-600 dark:text-slate-300">
        {chartData.map((entry) => (
          <li key={entry.key} className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: SEGMENT_COLOR[entry.key] ?? "#64748b" }}
              aria-hidden
            />
            <span>
              <span className="font-medium">{entry.name}</span>
              {": "}
              {formatNumber(entry.value)} users · {formatCurrency(entry.avgSpend)} avg
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
