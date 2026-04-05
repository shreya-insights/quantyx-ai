import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { transactionsService } from "@/services/transactions.service";

const STALE_5_MIN = 5 * 60 * 1000;

export function useAccounts() {
  return useQuery({
    queryKey: ["accounts"],
    queryFn: () => transactionsService.listAccounts(),
    staleTime: STALE_5_MIN,
  });
}

export function useCreateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof transactionsService.createAccount>[0]) =>
      transactionsService.createAccount(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
    retry: 0,
  });
}
