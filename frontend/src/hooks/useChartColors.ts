import { useThemeStore } from "@/stores/theme.store";

export function useChartColors() {
  const isDark = useThemeStore((s) => s.theme === "dark");
  return {
    grid:          isDark ? "#1e293b" : "#e2e8f0",
    tick:          isDark ? "#94a3b8" : "#64748b",
    tooltipBg:     isDark ? "#0f172a" : "#ffffff",
    tooltipBorder: isDark ? "#334155" : "#e2e8f0",
    series: [
      "#3b82f6",
      "#10b981",
      "#f59e0b",
      "#8b5cf6",
      "#ef4444",
      "#06b6d4",
      "#f97316",
    ],
  };
}
