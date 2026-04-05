import { useState } from "react";
import { TrendingUp } from "lucide-react";
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import {
  useRevenueTrends,
  useRFMAnalysis,
  useCohortRetention,
  useTopMerchants,
  useSpendingByCategory,
  useCohortRetentionGrid,
  useLTVSegments,
  useWarehouseHeatmap,
} from "../hooks/useAnalytics";
import { CohortRetentionTable } from "../components/CohortRetentionTable";
import { LTVSegmentChart } from "../components/LTVSegmentChart";
import { TransactionHeatmap } from "../components/TransactionHeatmap";
import { Skeleton } from "@/components/ui";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { formatCurrency, formatNumber } from "@/utils/format";
import { CHART_COLORS, SEGMENT_COLORS } from "@/utils/constants";
import { useChartColors } from "@/hooks/useChartColors";

type Tab =
  | "revenue"
  | "rfm"
  | "cohort"
  | "merchants"
  | "categories"
  | "cohort-retention"
  | "ltv"
  | "heatmap";

const TABS: { id: Tab; label: string }[] = [
  { id: "revenue",    label: "Revenue Trends" },
  { id: "rfm",        label: "RFM Segmentation" },
  { id: "cohort",     label: "Cohort Analysis" },
  { id: "cohort-retention", label: "WH · Cohort" },
  { id: "ltv",        label: "WH · LTV" },
  { id: "heatmap",    label: "WH · Heatmap" },
  { id: "merchants",  label: "Top Merchants" },
  { id: "categories", label: "Categories" },
];

export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("revenue");
  const c = useChartColors();

  const revenueQ    = useRevenueTrends(12);
  const rfmQ        = useRFMAnalysis();
  const cohortQ     = useCohortRetention();
  const whCohortQ   = useCohortRetentionGrid();
  const whLtvQ      = useLTVSegments();
  const whHeatQ     = useWarehouseHeatmap();
  const merchantsQ  = useTopMerchants(30, 15);
  const categoriesQ = useSpendingByCategory(30);

  const isLoading = {
    revenue:    revenueQ.isLoading,
    rfm:        rfmQ.isLoading,
    cohort:     cohortQ.isLoading,
    "cohort-retention": whCohortQ.isLoading,
    ltv:        whLtvQ.isLoading,
    heatmap:    whHeatQ.isLoading,
    merchants:  merchantsQ.isLoading,
    categories: categoriesQ.isLoading,
  }[activeTab];

  const tooltipStyle = {
    borderRadius: 8,
    border: `1px solid ${c.tooltipBorder}`,
    backgroundColor: c.tooltipBg,
    fontSize: 12,
  };

  return (
    <div className="p-6 lg:p-8">
      <PageHeader title="Analytics" subtitle="SQL-powered insights — window functions, CTEs, and aggregations" />

      {/* Tabs */}
      <div
        role="tablist"
        aria-label="Analytics tabs"
        className="flex gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-xl mb-6 overflow-x-auto"
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-shrink-0 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === tab.id
                ? "bg-white dark:bg-slate-700 text-brand-700 dark:text-brand-400 shadow-sm"
                : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-64 w-full rounded-xl" />
        </div>
      )}

      {/* Revenue Trends */}
      {!isLoading && activeTab === "revenue" && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-base font-semibold mb-1 text-slate-900 dark:text-slate-100">Monthly Revenue Trend (12 months)</h2>
          <p className="text-xs text-slate-400 font-mono mb-4">LAG() OVER (ORDER BY month) → MoM growth %</p>
          {(revenueQ.data?.data.length ?? 0) > 0 ? (
            <ResponsiveContainer minWidth={0} width="100%" height={320}>
              <LineChart data={revenueQ.data!.data}>
                <CartesianGrid strokeDasharray="3 3" stroke={c.grid} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: c.tick }} />
                <YAxis tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11, fill: c.tick }} />
                <Tooltip formatter={(v) => [formatCurrency(Number(v)), ""]} contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="inflow"   stroke="#3b82f6" strokeWidth={2.5} dot={false} name="Inflow"   isAnimationActive animationDuration={800} animationEasing="ease-out" />
                <Line type="monotone" dataKey="outflow"  stroke="#f59e0b" strokeWidth={2.5} dot={false} name="Outflow"  isAnimationActive animationDuration={900} animationEasing="ease-out" />
                <Line type="monotone" dataKey="net_flow" stroke="#10b981" strokeWidth={2}   dot={false} strokeDasharray="5 5" name="Net Flow" isAnimationActive animationDuration={1000} animationEasing="ease-out" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState icon={TrendingUp} title="No data to analyze" description="Analytics require at least 30 days of transaction history. Upload a CSV to get started." className="h-52" />
          )}
        </div>
      )}

      {/* RFM Segmentation */}
      {!isLoading && activeTab === "rfm" && (
        <div className="grid lg:grid-cols-2 xl:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
            <h2 className="text-base font-semibold mb-1 text-slate-900 dark:text-slate-100">Customer Segments</h2>
            <p className="text-xs text-slate-400 font-mono mb-4">NTILE(5) OVER recency/frequency/monetary → CASE segments</p>
            {(rfmQ.data?.segments.length ?? 0) > 0 ? (
              <ResponsiveContainer minWidth={0} width="100%" height={280}>
                <PieChart>
                  <Pie data={rfmQ.data!.segments} dataKey="customer_count" nameKey="segment" cx="50%" cy="50%" outerRadius={100} isAnimationActive animationBegin={0} animationDuration={700}>
                    {rfmQ.data!.segments.map((entry, idx) => (
                      <Cell key={entry.segment} fill={SEGMENT_COLORS[entry.segment] ?? CHART_COLORS[idx % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => [formatNumber(Number(v)), "Customers"]} contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState icon={TrendingUp} title="No customer data" description="RFM segmentation needs at least 90 days of transaction history." className="h-52" />
            )}
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
            <h2 className="text-base font-semibold mb-4 text-slate-900 dark:text-slate-100">Segment Revenue Breakdown</h2>
            <div className="space-y-3">
              {(rfmQ.data?.segments ?? []).map((seg, idx) => (
                <div key={seg.segment} className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: SEGMENT_COLORS[seg.segment] ?? CHART_COLORS[idx % CHART_COLORS.length] }} />
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-medium text-slate-700 dark:text-slate-300 truncate">{seg.segment}</span>
                      <span className="text-slate-400 flex-shrink-0 ml-2">{seg.customer_count} customers</span>
                    </div>
                    <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full" style={{ width: `${seg.pct_of_total}%`, backgroundColor: SEGMENT_COLORS[seg.segment] ?? CHART_COLORS[idx] }} />
                    </div>
                  </div>
                  <span className="text-xs text-slate-400 w-20 text-right flex-shrink-0">{formatCurrency(seg.total_revenue)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Cohort Analysis */}
      {!isLoading && activeTab === "cohort" && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-base font-semibold mb-1 text-slate-900 dark:text-slate-100">Cohort Retention Matrix</h2>
          <p className="text-xs text-slate-400 font-mono mb-4">PERIOD_DIFF(tx_month, cohort_month) → retention % per period</p>
          {(cohortQ.data?.data.length ?? 0) > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <caption className="sr-only">Cohort retention matrix — percentage of customers retained each month</caption>
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700">
                    {["Cohort", "Size", "M+0", "M+1", "M+2", "M+3", "M+6", "M+12"].map((h) => (
                      <th key={h} scope="col" className={`py-3 px-3 text-xs font-medium text-slate-500 dark:text-slate-400 ${h === "Cohort" ? "text-left" : "text-center"}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {cohortQ.data!.data.map((row) => (
                    <tr key={row.cohort_month} className="border-b border-slate-50 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30">
                      <td className="py-3 px-3 font-medium text-slate-800 dark:text-slate-200">{row.cohort_month}</td>
                      <td className="py-3 px-3 text-center text-slate-500 dark:text-slate-400 text-xs">{formatNumber(row.cohort_size)}</td>
                      {(["period_0","period_1","period_2","period_3","period_6","period_12"] as const).map((p) => {
                        const val = row[p];
                        return (
                          <td key={p} className="py-3 px-3 text-center">
                            {val != null ? (
                              <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                                val >= 80 ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300" :
                                val >= 50 ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300" :
                                val >= 20 ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300" :
                                "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
                              }`}>{val}%</span>
                            ) : <span className="text-slate-300 dark:text-slate-600">—</span>}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState icon={TrendingUp} title="No cohort data" description="Cohort analysis needs at least 2 months of transaction data to build the retention matrix." className="h-52" />
          )}
        </div>
      )}

      {/* Top Merchants */}
      {!isLoading && activeTab === "merchants" && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-base font-semibold mb-1 text-slate-900 dark:text-slate-100">Top Merchants by Revenue</h2>
          <p className="text-xs text-slate-400 font-mono mb-4">RANK() OVER (PARTITION BY category_code ORDER BY revenue DESC) · SUM OVER () for share %</p>
          {(merchantsQ.data?.data.length ?? 0) > 0 ? (
            <ResponsiveContainer minWidth={0} width="100%" height={340}>
              <BarChart data={merchantsQ.data!.data.slice(0, 10)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={c.grid} />
                <XAxis type="number" tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11, fill: c.tick }} />
                <YAxis type="category" dataKey="merchant_name" tick={{ fontSize: 11, fill: c.tick }} width={130} />
                <Tooltip formatter={(v) => [formatCurrency(Number(v)), "Revenue"]} contentStyle={tooltipStyle} />
                <Bar dataKey="total_revenue" fill="#6366f1" radius={[0, 4, 4, 0]} isAnimationActive animationDuration={600} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState icon={TrendingUp} title="No merchant data" description="Merchant rankings will appear once transaction data is loaded." className="h-52" />
          )}
        </div>
      )}

      {/* Warehouse: cohort retention grid */}
      {!isLoading && activeTab === "cohort-retention" && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-base font-semibold mb-1 text-slate-900 dark:text-slate-100">
            Warehouse cohort retention
          </h2>
          <p className="text-xs text-slate-400 font-mono mb-4">
            Pre-aggregated nightly ETL · cell = retention % by cohort month × M+N
          </p>
          {(whCohortQ.data?.rows.length ?? 0) > 0 && whCohortQ.data ? (
            <CohortRetentionTable data={whCohortQ.data} />
          ) : (
            <EmptyState
              icon={TrendingUp}
              title="No warehouse cohort data"
              description="Run the nightly ETL or ensure users and completed transactions exist. Data appears after quantyx.warehouse.run_nightly_etl populates the warehouse."
              className="h-52"
            />
          )}
        </div>
      )}

      {/* Warehouse: LTV */}
      {!isLoading && activeTab === "ltv" && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-base font-semibold mb-1 text-slate-900 dark:text-slate-100">
            LTV segments (warehouse)
          </h2>
          <p className="text-xs text-slate-400 font-mono mb-4">
            Tertiles from p33 / p66 spend thresholds on lifetime totals
          </p>
          {(whLtvQ.data?.segments.length ?? 0) > 0 && whLtvQ.data ? (
            <LTVSegmentChart data={whLtvQ.data} />
          ) : (
            <EmptyState
              icon={TrendingUp}
              title="No LTV warehouse rows"
              description="LTV metrics are built from per-user completed transaction totals during nightly warehouse ETL."
              className="h-52"
            />
          )}
        </div>
      )}

      {/* Warehouse: 7×24 heatmap */}
      {!isLoading && activeTab === "heatmap" && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-base font-semibold mb-1 text-slate-900 dark:text-slate-100">
            Transaction intensity heatmap
          </h2>
          <p className="text-xs text-slate-400 font-mono mb-4">
            7×24 grid · avg_count / week slot from last 90 days (warehouse)
          </p>
          {whHeatQ.data ? (
            <TransactionHeatmap data={whHeatQ.data} />
          ) : (
            <EmptyState
              icon={TrendingUp}
              title="No heatmap data"
              description="Heatmap loads from the warehouse after ETL runs."
              className="h-52"
            />
          )}
        </div>
      )}

      {/* Categories */}
      {!isLoading && activeTab === "categories" && (
        <div className="grid lg:grid-cols-2 xl:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
            <h2 className="text-base font-semibold mb-4 text-slate-900 dark:text-slate-100">Spending by Category</h2>
            {(categoriesQ.data?.length ?? 0) > 0 ? (
              <ResponsiveContainer minWidth={0} width="100%" height={280}>
                <PieChart>
                  <Pie data={categoriesQ.data} dataKey="total_amount" nameKey="category_name" cx="50%" cy="50%" outerRadius={100} isAnimationActive animationBegin={0} animationDuration={700}>
                    {categoriesQ.data!.map((_, idx) => (
                      <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState icon={TrendingUp} title="No category data" description="Spending breakdown by category will appear once transactions are uploaded." className="h-52" />
            )}
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
            <h2 className="text-base font-semibold mb-4 text-slate-900 dark:text-slate-100">Breakdown</h2>
            <div className="space-y-3">
              {(categoriesQ.data ?? []).map((cat, idx) => (
                <div key={cat.category_name} className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] }} />
                  <div className="flex-1">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-medium text-slate-700 dark:text-slate-300">{cat.category_name}</span>
                      <span className="text-slate-400">{cat.pct_of_total}%</span>
                    </div>
                    <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full" style={{ width: `${cat.pct_of_total}%`, backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] }} />
                    </div>
                  </div>
                  <span className="text-xs text-slate-400 w-20 text-right">{formatCurrency(cat.total_amount)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
