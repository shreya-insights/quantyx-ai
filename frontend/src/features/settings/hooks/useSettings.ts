import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { subscriptionsService } from "@/services/subscriptions.service";

export function usePlans() {
  return useQuery({
    queryKey: ["plans"],
    queryFn: () => subscriptionsService.getPlans(),
    staleTime: Infinity,
  });
}

export function useUsage() {
  return useQuery({
    queryKey: ["usage"],
    queryFn: () => subscriptionsService.getUsage(),
    staleTime: 60_000,
  });
}

export function useSubscribe() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ planName, cycle }: { planName: string; cycle: "monthly" | "annual" }) =>
      subscriptionsService.subscribe(planName, cycle),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["usage"] });
    },
  });
}
