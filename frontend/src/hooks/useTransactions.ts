import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  transactionsService,
  type CreateTransactionPayload,
  type TransactionFilters,
} from "@/services/transactions.service";
import type { PaginatedResponse, Transaction } from "@/types/api.types";

const STALE_1_MIN = 60 * 1000;

export function useTransactions(filters: TransactionFilters = {}) {
  return useQuery({
    queryKey: ["transactions", filters],
    queryFn: () => transactionsService.list(filters),
    staleTime: STALE_1_MIN,
    // Transform once here — components receive clean data, not raw API shape
    select: (data: PaginatedResponse<Transaction>) => data,
    // Smooth pagination: keep previous page visible while next page loads
    placeholderData: keepPreviousData,
  });
}

export function useTransaction(id: number) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: ["transaction", id],
    queryFn: () =>
      transactionsService
        .list({ page: 1, page_size: 100 })
        .then((resp) => resp.data.find((t) => t.id === id) ?? null),
    staleTime: STALE_1_MIN,
    // Seed from any cached list to avoid a redundant network round-trip
    initialData: () => {
      const lists = queryClient
        .getQueriesData<PaginatedResponse<Transaction>>({
          queryKey: ["transactions"],
        })
        .flatMap(([, data]) => data?.data ?? []);
      return lists.find((t) => t.id === id) ?? undefined;
    },
  });
}

export function useCreateTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateTransactionPayload) =>
      transactionsService.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["kpi-summary"] });
      queryClient.invalidateQueries({ queryKey: ["revenue-trends"] });
    },
    retry: 0,
  });
}

export function useBulkUpload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => transactionsService.bulkUpload(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["kpi-summary"] });
      queryClient.invalidateQueries({ queryKey: ["revenue-trends"] });
    },
    retry: 0,
  });
}
