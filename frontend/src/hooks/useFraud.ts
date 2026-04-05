import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { fraudService, type AlertFilters } from "@/services/fraud.service";
import type { FraudAlert, PaginatedResponse } from "@/types/api.types";

const STALE_30S = 30_000;
const REFETCH_30S = 30_000;
const STALE_1_MIN = 60_000;

export function useFraudAlerts(filters: AlertFilters = {}) {
  return useQuery({
    queryKey: ["fraud-alerts", filters],
    queryFn: () => fraudService.getAlerts(filters),
    staleTime: STALE_30S,
    // Poll every 30 seconds to give a real-time feel without WebSocket dependency
    refetchInterval: REFETCH_30S,
  });
}

export function useFraudAlert(id: number) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: ["fraud-alert", id],
    queryFn: () =>
      fraudService
        .getAlerts({ page: 1, page_size: 100 })
        .then((resp) => resp.data.find((a) => a.id === id) ?? null),
    staleTime: STALE_30S,
    // Seed from any cached list query to avoid a redundant network round-trip
    initialData: () => {
      const lists = queryClient
        .getQueriesData<PaginatedResponse<FraudAlert>>({
          queryKey: ["fraud-alerts"],
        })
        .flatMap(([, data]) => data?.data ?? []);
      return lists.find((a) => a.id === id) ?? undefined;
    },
  });
}

export function useFraudStats() {
  return useQuery({
    queryKey: ["fraud-stats"],
    queryFn: () => fraudService.getStats(),
    staleTime: STALE_1_MIN,
  });
}

export function useResolveFraud() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, note }: { id: number; note?: string }) =>
      fraudService.resolveAlert(id, note),
    onMutate: async ({ id }) => {
      // Cancel in-flight queries so they don't overwrite the optimistic update
      await queryClient.cancelQueries({ queryKey: ["fraud-alerts"] });
      const previous = queryClient.getQueriesData({ queryKey: ["fraud-alerts"] });
      // Optimistically mark the alert as resolved in every cached list
      queryClient.setQueriesData(
        { queryKey: ["fraud-alerts"] },
        (old: unknown) => {
          if (!old || typeof old !== "object") return old;
          const page = old as PaginatedResponse<FraudAlert>;
          if (!Array.isArray(page.data)) return old;
          return {
            ...page,
            data: page.data.map((a) =>
              a.id === id ? { ...a, is_resolved: true } : a
            ),
          };
        }
      );
      return { previous };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) {
        ctx.previous.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["fraud-alerts"] });
      queryClient.invalidateQueries({ queryKey: ["fraud-stats"] });
    },
    retry: 0,
  });
}

// Alias for legacy usages that imported useResolveAlert
export { useResolveFraud as useResolveAlert };
