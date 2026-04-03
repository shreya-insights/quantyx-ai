import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fraudService, type AlertFilters } from "@/services/fraud.service";

export function useFraudAlerts(filters: AlertFilters) {
  return useQuery({
    queryKey: ["fraud-alerts", filters],
    queryFn: () => fraudService.getAlerts(filters),
    staleTime: 30_000,
  });
}

export function useFraudStats() {
  return useQuery({
    queryKey: ["fraud-stats"],
    queryFn: () => fraudService.getStats(),
    staleTime: 60_000,
  });
}

export function useResolveAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, note }: { id: number; note?: string }) =>
      fraudService.resolveAlert(id, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fraud-alerts"] });
      qc.invalidateQueries({ queryKey: ["fraud-stats"] });
    },
  });
}
