import { useState } from "react";
import { Users, CreditCard, Check } from "lucide-react";
import { usePlans, useUsage, useSubscribe } from "../hooks/useSettings";
import { Button, Skeleton } from "@/components/ui";
import { PageHeader } from "@/components/common/PageHeader";
import { useAuthStore } from "@/stores/auth.store";

type Tab = "profile" | "subscription" | "usage";

const PLAN_BORDER: Record<string, string> = {
  starter:    "border-slate-200 dark:border-slate-700",
  growth:     "border-blue-400 shadow-blue-900/10",
  enterprise: "border-violet-500 shadow-violet-900/10",
};

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>("profile");
  const { user } = useAuthStore();

  const plansQuery    = usePlans();
  const usageQuery    = useUsage();
  const subscribeMutation = useSubscribe();

  return (
    <div className="p-6 lg:p-8">
      <PageHeader title="Settings" subtitle="Account, subscription, and preferences" />

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-xl mb-6 w-fit">
        {(["profile", "subscription", "usage"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors capitalize ${
              tab === t
                ? "bg-white dark:bg-slate-700 text-blue-700 dark:text-blue-400 shadow-sm"
                : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Profile */}
      {tab === "profile" && (
        <div className="max-w-xl space-y-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
            <h2 className="font-semibold text-slate-900 dark:text-slate-100 mb-4">Your Profile</h2>
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-violet-600 rounded-full flex items-center justify-center text-xl font-bold text-white flex-shrink-0">
                {user?.full_name?.[0]?.toUpperCase() ?? "U"}
              </div>
              <div>
                <p className="font-semibold text-slate-900 dark:text-slate-100">{user?.full_name ?? "—"}</p>
                <p className="text-sm text-slate-400">{user?.email}</p>
                <span className="inline-block text-xs bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full mt-1 capitalize">
                  {user?.role}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Subscription */}
      {tab === "subscription" && (
        <div className="grid md:grid-cols-3 gap-4 max-w-4xl">
          {plansQuery.isLoading
            ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-64 rounded-xl" />)
            : plansQuery.data?.map((plan) => (
              <div
                key={plan.name}
                className={`bg-white dark:bg-slate-800 rounded-2xl border-2 ${PLAN_BORDER[plan.name] ?? "border-slate-200 dark:border-slate-700"} p-6 flex flex-col shadow-md`}
              >
                <div className="mb-4">
                  <h3 className="text-lg font-bold capitalize text-slate-900 dark:text-slate-100">{plan.name}</h3>
                  <div className="mt-1">
                    <span className="text-3xl font-bold text-slate-900 dark:text-slate-100">${plan.monthly_price}</span>
                    <span className="text-slate-400 text-sm">/month</span>
                  </div>
                </div>

                <ul className="space-y-2 mb-6 flex-1 text-sm">
                  <li className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400">
                    <Users size={14} className="text-slate-400 flex-shrink-0" aria-hidden="true" />
                    {plan.user_limit ? `${plan.user_limit} users` : "Unlimited users"}
                  </li>
                  <li className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400">
                    <CreditCard size={14} className="text-slate-400 flex-shrink-0" aria-hidden="true" />
                    {plan.transaction_limit ? plan.transaction_limit.toLocaleString() : "Unlimited"} tx/month
                  </li>
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400">
                      <Check size={13} className="text-emerald-500 flex-shrink-0" aria-hidden="true" />
                      <span className="capitalize">{f.replace(/_/g, " ")}</span>
                    </li>
                  ))}
                </ul>

                <Button
                  variant={usageQuery.data?.plan_name === plan.name ? "secondary" : "primary"}
                  disabled={usageQuery.data?.plan_name === plan.name}
                  loading={subscribeMutation.isPending && subscribeMutation.variables?.planName === plan.name}
                  onClick={() => subscribeMutation.mutate({ planName: plan.name, cycle: "monthly" })}
                  className="w-full"
                >
                  {usageQuery.data?.plan_name === plan.name ? "Current Plan" : "Subscribe"}
                </Button>
              </div>
            ))}
        </div>
      )}

      {/* Usage */}
      {tab === "usage" && (
        <div className="max-w-md">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
            <h2 className="font-semibold text-slate-900 dark:text-slate-100 mb-4">Current Usage</h2>
            {usageQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            ) : usageQuery.data ? (
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1.5">
                    <span className="text-slate-600 dark:text-slate-400">API Calls This Month</span>
                    <span className="font-medium text-slate-900 dark:text-slate-100">
                      {usageQuery.data.api_calls_used.toLocaleString()} / {usageQuery.data.api_calls_limit?.toLocaleString() ?? "∞"}
                    </span>
                  </div>
                  {usageQuery.data.api_calls_limit && (
                    <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all ${(usageQuery.data.usage_pct ?? 0) >= 80 ? "bg-red-500" : "bg-blue-500"}`}
                        style={{ width: `${Math.min(usageQuery.data.usage_pct ?? 0, 100)}%` }}
                      />
                    </div>
                  )}
                </div>

                <div className="flex justify-between text-sm">
                  <span className="text-slate-600 dark:text-slate-400">Transactions This Month</span>
                  <span className="font-medium text-slate-900 dark:text-slate-100">
                    {usageQuery.data.transaction_count_this_month.toLocaleString()} / {usageQuery.data.transaction_limit?.toLocaleString() ?? "∞"}
                  </span>
                </div>

                <div className="flex justify-between text-sm pt-2 border-t border-slate-100 dark:border-slate-700">
                  <span className="text-slate-600 dark:text-slate-400">Current Plan</span>
                  <span className="font-semibold text-blue-600 dark:text-blue-400 capitalize">{usageQuery.data.plan_name}</span>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
