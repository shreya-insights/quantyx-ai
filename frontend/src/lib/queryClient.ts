import { QueryClient } from "@tanstack/react-query";
import useNotificationStore from "@/stores/notification.store";

const STALE_2_MIN = 2 * 60 * 1000;
const GC_10_MIN = 10 * 60 * 1000;
const MAX_RETRY_DELAY_MS = 5_000;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Financial data: stale after 2 minutes, keep in cache 10 minutes
      staleTime: STALE_2_MIN,
      gcTime: GC_10_MIN,
      // Retry once with exponential backoff; never retry 4xx (client errors)
      retry: (failureCount, error) => {
        const status = (error as { response?: { status?: number } })?.response
          ?.status;
        if (status !== undefined && status >= 400 && status < 500) return false;
        return failureCount < 1;
      },
      retryDelay: (attempt) =>
        Math.min(1_000 * 2 ** attempt, MAX_RETRY_DELAY_MS),
      // Refetch when window regains focus — financial data must be fresh
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
    mutations: {
      // Mutations are never retried — idempotency is not guaranteed
      retry: 0,
      onError: (error: unknown) => {
        const message =
          error instanceof Error ? error.message : "An unexpected error occurred";
        useNotificationStore.getState().addNotification({
          type: "error",
          title: "Action Failed",
          message,
        });
      },
    },
  },
});
