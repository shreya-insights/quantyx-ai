import { useQuery } from "@tanstack/react-query";
import { analyticsService } from "@/services/analytics.service";

export function useKpiSummary(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["kpi-summary", startDate, endDate],
    queryFn: () => analyticsService.getKpiSummary(startDate, endDate),
    staleTime: 5 * 60 * 1000,
  });
}

export function useRevenueTrends(months = 6) {
  return useQuery({
    queryKey: ["revenue-trends", months],
    queryFn: () => analyticsService.getRevenueTrends(months),
    staleTime: 15 * 60 * 1000,
  });
}
