import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { transactionsService } from "@/services/transactions.service";
import type { Merchant } from "@/types/api.types";

const STALE_10_MIN = 10 * 60 * 1000;

export function useMerchants() {
  return useQuery({
    queryKey: ["merchants"],
    queryFn: () => transactionsService.listMerchants(),
    staleTime: STALE_10_MIN,
  });
}

export function useFlagMerchant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (merchantId: number) =>
      transactionsService.flagMerchant(merchantId),
    onMutate: async (merchantId) => {
      await queryClient.cancelQueries({ queryKey: ["merchants"] });
      const previous = queryClient.getQueryData<Merchant[]>(["merchants"]);
      queryClient.setQueryData<Merchant[]>(["merchants"], (old) =>
        old?.map((m) =>
          m.id === merchantId ? { ...m, is_flagged: true } : m
        ) ?? []
      );
      return { previous };
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.previous) {
        queryClient.setQueryData(["merchants"], ctx.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["merchants"] });
    },
    retry: 0,
  });
}
