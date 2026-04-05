import type { HeatmapResponse } from "@/types/api.types";

const DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

interface Props {
  data: HeatmapResponse;
}

export function TransactionHeatmap({ data }: Props) {
  const bySlot = new Map<string, number>();
  for (const c of data.cells) {
    bySlot.set(`${c.day_of_week}-${c.hour_of_day}`, c.avg_count);
  }
  const maxCount = Math.max(0, ...data.cells.map((c) => c.avg_count), 1e-6);

  return (
    <div className="space-y-2">
      <div
        className="inline-grid gap-px rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-200 dark:bg-slate-600 p-px overflow-x-auto"
        style={{
          gridTemplateColumns: `4rem repeat(24, minmax(0.65rem, 1fr))`,
        }}
        role="grid"
        aria-label="Transaction count heatmap by weekday and hour"
      >
        <div className="bg-slate-50 dark:bg-slate-800/90" />
        {Array.from({ length: 24 }, (_, h) => (
          <div
            key={`h-${h}`}
            className="text-[9px] text-center text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/90 py-1 font-mono"
          >
            {h}
          </div>
        ))}
        {DOW_LABELS.flatMap((label, dow) => [
          <div
            key={`l-${dow}`}
            className="flex items-center justify-end pr-2 text-[10px] font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-900 py-0.5"
          >
            {label}
          </div>,
          ...Array.from({ length: 24 }, (_, hod) => {
            const v = bySlot.get(`${dow}-${hod}`) ?? 0;
            const t = Math.min(1, v / maxCount);
            const title = `Avg tx ~${v.toFixed(2)} / week slot (intensity ${(t * 100).toFixed(0)}%)`;
            return (
              <div
                key={`${dow}-${hod}`}
                role="gridcell"
                title={title}
                aria-label={title}
                className="aspect-square min-w-[11px] min-h-[11px] rounded-[2px] bg-blue-500"
                style={{ opacity: 0.12 + t * 0.88 }}
              />
            );
          }),
        ])}
      </div>
      <p className="text-[10px] text-slate-500 dark:text-slate-400">
        Cell color intensity maps to avg transaction count per weekday/hour (warehouse 90-day window).
      </p>
    </div>
  );
}
