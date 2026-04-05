import { useQuery } from "@tanstack/react-query";
import { analyticsService } from "@/services/analytics.service";

const STALE_5_MIN = 5 * 60 * 1000;
const STALE_10_MIN = 10 * 60 * 1000;
const STALE_30_MIN = 30 * 60 * 1000;
const STALE_60_MIN = 60 * 60 * 1000;

// ─── Dashboard ───────────────────────────────────────────────────────────────

export function useKPISummary(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["kpi-summary", startDate, endDate],
    queryFn: () => analyticsService.getKpiSummary(startDate, endDate),
    staleTime: STALE_5_MIN,
  });
}

// ─── Revenue ─────────────────────────────────────────────────────────────────

export function useRevenueTrend(months = 12) {
  return useQuery({
    queryKey: ["revenue-trends", months],
    queryFn: () => analyticsService.getRevenueTrends(months),
    staleTime: STALE_5_MIN,
  });
}

// Alias kept for backward compat with useDashboard consumers
export { useRevenueTrend as useRevenueTrends };

// ─── Category & merchants ────────────────────────────────────────────────────

export function useTopMerchants(days = 30, topN = 15) {
  return useQuery({
    queryKey: ["top-merchants", days, topN],
    queryFn: () => analyticsService.getTopMerchants(days, topN),
    staleTime: STALE_5_MIN,
  });
}

// ─── Segmentation — cohort data changes slowly ───────────────────────────────

export function useRFMSegments() {
  return useQuery({
    queryKey: ["rfm-segmentation"],
    queryFn: () => analyticsService.getCustomerSegmentation(),
    staleTime: STALE_30_MIN,
  });
}

// Alias matching original feature hook name
export { useRFMSegments as useRFMAnalysis };

export function useSpendingByCategory(days = 30) {
  return useQuery({
    queryKey: ["spending-category", days],
    queryFn: () => analyticsService.getSpendingByCategory(days),
    staleTime: STALE_10_MIN,
  });
}

// ─── Data Warehouse views ────────────────────────────────────────────────────

export function useCohortRetention() {
  return useQuery({
    queryKey: ["cohort-retention"],
    queryFn: () => analyticsService.getCohortRetention(),
    staleTime: STALE_60_MIN,
  });
}

export function useCohortRetentionGrid() {
  return useQuery({
    queryKey: ["warehouse-cohort-retention"],
    queryFn: () => analyticsService.getCohortRetentionGrid(),
    staleTime: STALE_60_MIN,
  });
}

export function useLTVSegments() {
  return useQuery({
    queryKey: ["warehouse-ltv-segments"],
    queryFn: () => analyticsService.getLTVSegments(),
    staleTime: STALE_60_MIN,
  });
}

export function useWarehouseHeatmap() {
  return useQuery({
    queryKey: ["warehouse-heatmap"],
    queryFn: () => analyticsService.getWarehouseHeatmap(),
    staleTime: STALE_60_MIN,
  });
}
