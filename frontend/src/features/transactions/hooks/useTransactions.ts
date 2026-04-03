import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { transactionsService, type TransactionFilters } from "@/services/transactions.service";

export function useTransactions(filters: TransactionFilters) {
  return useQuery({
    queryKey: ["transactions", filters],
    queryFn: () => transactionsService.list(filters),
    staleTime: 30_000,
  });
}

export function useBulkUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => transactionsService.bulkUpload(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["kpi-summary"] });
      qc.invalidateQueries({ queryKey: ["revenue-trends"] });
    },
  });
}

export function useAccounts() {
  return useQuery({
    queryKey: ["accounts"],
    queryFn: () => transactionsService.listAccounts(),
    staleTime: 5 * 60 * 1000,
  });
}
