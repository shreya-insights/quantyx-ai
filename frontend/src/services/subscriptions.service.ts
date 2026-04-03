import { api } from "@/lib/axios";
import type { PlanDetails, Subscription, UsageStats } from "@/types/api.types";

export const subscriptionsService = {
  getPlans: () => api.get<PlanDetails[]>("/subscriptions/plans").then((r) => r.data),

  getCurrent: () => api.get<Subscription>("/subscriptions/current").then((r) => r.data),

  getUsage: () => api.get<UsageStats>("/subscriptions/usage").then((r) => r.data),

  subscribe: (planName: string, billingCycle: "monthly" | "annual" = "monthly") =>
    api
      .post<Subscription>("/subscriptions/subscribe", {
        plan_name: planName,
        billing_cycle: billingCycle,
      })
      .then((r) => r.data),
};
