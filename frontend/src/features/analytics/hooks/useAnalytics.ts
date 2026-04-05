import { useQuery } from "@tanstack/react-query";
import { analyticsService } from "@/services/analytics.service";

export function useRevenueTrends(months = 12) {
  return useQuery({
    queryKey: ["revenue-trends", months],
    queryFn: () => analyticsService.getRevenueTrends(months),
    staleTime: 15 * 60 * 1000,
  });
}

export function useRFMAnalysis() {
  return useQuery({
    queryKey: ["rfm-segmentation"],
    queryFn: () => analyticsService.getCustomerSegmentation(),
    staleTime: 30 * 60 * 1000,
  });
}

export function useCohortRetention() {
  return useQuery({
    queryKey: ["cohort-retention"],
    queryFn: () => analyticsService.getCohortRetention(),
    staleTime: 60 * 60 * 1000,
  });
}

export function useTopMerchants(days = 30, topN = 15) {
  return useQuery({
    queryKey: ["top-merchants", days, topN],
    queryFn: () => analyticsService.getTopMerchants(days, topN),
    staleTime: 10 * 60 * 1000,
  });
}

export function useSpendingByCategory(days = 30) {
  return useQuery({
    queryKey: ["spending-category", days],
    queryFn: () => analyticsService.getSpendingByCategory(days),
    staleTime: 10 * 60 * 1000,
  });
}

export function useCohortRetentionGrid() {
  return useQuery({
    queryKey: ["warehouse-cohort-retention"],
    queryFn: () => analyticsService.getCohortRetentionGrid(),
    staleTime: 60 * 60 * 1000,
  });
}

export function useLTVSegments() {
  return useQuery({
    queryKey: ["warehouse-ltv-segments"],
    queryFn: () => analyticsService.getLTVSegments(),
    staleTime: 60 * 60 * 1000,
  });
}

export function useWarehouseHeatmap() {
  return useQuery({
    queryKey: ["warehouse-heatmap"],
    queryFn: () => analyticsService.getWarehouseHeatmap(),
    staleTime: 60 * 60 * 1000,
  });
}
