import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import {
  DollarSign,
  ArrowDownToLine,
  ArrowUpFromLine,
  RefreshCw,
  Users,
  BarChart3,
  AlertOctagon,
  ShieldAlert,
  BarChart2,
} from "lucide-react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { useKpiSummary, useRevenueTrends } from "../hooks/useDashboard";
import { LiveFeedPanel } from "../components/LiveFeedPanel";
import { StatCard, KpiCardSkeleton } from "@/components/ui";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { formatCurrency, formatNumber, formatPercent } from "@/utils/format";
import { useChartColors } from "@/hooks/useChartColors";
import { useAuthStore } from "@/stores/auth.store";

const cardContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.04 } },
};

const cardItem = {
  hidden: { opacity: 0, y: 16, scale: 0.97 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.22, ease: [0.4, 0, 0.2, 1] as const },
  },
};

export default function DashboardPage() {
  const kpiQuery   = useKpiSummary();
  const trendQuery = useRevenueTrends(6);
  const c          = useChartColors();
  const { user }   = useAuthStore();

  const kpi   = kpiQuery.data;
  const trend = trendQuery.data?.data ?? [];

  const tooltipStyle = {
    borderRadius: 8,
    border: `1px solid ${c.tooltipBorder}`,
    backgroundColor: c.tooltipBg,
    fontSize: 12,
  };

  return (
    <div className="p-6 lg:p-8">
      <PageHeader
        title="Dashboard"
        subtitle="Financial intelligence overview — last 30 days"
      />

      {/* KPI Cards */}
      {kpiQuery.isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {Array.from({ length: 8 }).map((_, i) => <KpiCardSkeleton key={i} />)}
        </div>
      ) : (
        <motion.div
          variants={cardContainer}
          initial="hidden"
          animate="show"
          className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-4 gap-4 mb-8"
        >
          {[
            { title: "Total Volume",     value: formatCurrency(kpi?.total_volume ?? 0),              rawValue: kpi?.total_volume,              icon: DollarSign,     colorClass: "bg-blue-50 border-blue-100 dark:bg-blue-900/10 dark:border-blue-900/30",         iconClass: "text-brand-600 dark:text-brand-400" },
            { title: "Total Inflow",     value: formatCurrency(kpi?.total_inflow ?? 0),              rawValue: kpi?.total_inflow,              icon: ArrowDownToLine, colorClass: "bg-emerald-50 border-emerald-100 dark:bg-emerald-900/10 dark:border-emerald-900/30", iconClass: "text-emerald-600 dark:text-emerald-400" },
            { title: "Total Outflow",    value: formatCurrency(kpi?.total_outflow ?? 0),             rawValue: kpi?.total_outflow,             icon: ArrowUpFromLine, colorClass: "bg-amber-50 border-amber-100 dark:bg-amber-900/10 dark:border-amber-900/30",     iconClass: "text-amber-600 dark:text-amber-400" },
            { title: "Transactions",     value: formatNumber(kpi?.total_transactions ?? 0),          rawValue: kpi?.total_transactions,        icon: RefreshCw,       colorClass: "bg-violet-50 border-violet-100 dark:bg-violet-900/10 dark:border-violet-900/30",   iconClass: "text-violet-600 dark:text-violet-400" },
            { title: "Unique Customers", value: formatNumber(kpi?.unique_customers ?? 0),            rawValue: kpi?.unique_customers,          icon: Users,           colorClass: "bg-blue-50 border-blue-100 dark:bg-blue-900/10 dark:border-blue-900/30",         iconClass: "text-brand-600 dark:text-brand-400" },
            { title: "Avg Transaction",  value: formatCurrency(kpi?.avg_transaction_value ?? 0),     rawValue: kpi?.avg_transaction_value,     icon: BarChart3,       colorClass: "bg-violet-50 border-violet-100 dark:bg-violet-900/10 dark:border-violet-900/30",   iconClass: "text-violet-600 dark:text-violet-400" },
            { title: "Fraud Alerts",     value: formatNumber(kpi?.fraud_alert_count ?? 0),           rawValue: kpi?.fraud_alert_count,         icon: AlertOctagon,    colorClass: "bg-red-50 border-red-100 dark:bg-red-900/10 dark:border-red-900/30",             iconClass: "text-red-600 dark:text-red-400" },
            { title: "Fraud Rate",       value: `${(kpi?.fraud_alert_rate_pct ?? 0).toFixed(4)}%`,  rawValue: undefined,                      icon: ShieldAlert,     colorClass: "bg-red-50 border-red-100 dark:bg-red-900/10 dark:border-red-900/30",             iconClass: "text-red-600 dark:text-red-400" },
          ].map((card) => (
            <motion.div key={card.title} variants={cardItem}>
              <StatCard
                title={card.title}
                value={card.value}
                rawValue={card.rawValue}
                icon={card.icon}
                colorClass={card.colorClass}
                iconClass={card.iconClass}
              />
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Charts */}
      <div className="grid lg:grid-cols-2 xl:grid-cols-2 gap-6 mb-8">
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-0.5">Revenue Trend</h2>
          <p className="text-xs text-slate-400 mb-4">Monthly inflow vs outflow — last 6 months</p>
          {trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke={c.grid} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: c.tick }} />
                <YAxis tick={{ fontSize: 11, fill: c.tick }} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
                <Tooltip formatter={(v) => [formatCurrency(Number(v)), ""]} contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="inflow"  stroke="#3b82f6" strokeWidth={2} dot={false} name="Inflow"  isAnimationActive animationDuration={800} animationEasing="ease-out" />
                <Line type="monotone" dataKey="outflow" stroke="#f59e0b" strokeWidth={2} dot={false} name="Outflow" isAnimationActive animationDuration={900} animationEasing="ease-out" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState
              icon={BarChart2}
              title="Awaiting data"
              description="Upload transactions and your charts will appear here."
              action={<Link to="/transactions" className="text-sm text-brand-600 dark:text-brand-400 hover:underline font-medium">Upload transactions</Link>}
              className="h-52"
            />
          )}
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-0.5">Net Cash Flow</h2>
          <p className="text-xs text-slate-400 mb-4">Monthly net flow (inflow − outflow)</p>
          {trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke={c.grid} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: c.tick }} />
                <YAxis tick={{ fontSize: 11, fill: c.tick }} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
                <Tooltip formatter={(v) => [formatCurrency(Number(v)), "Net Flow"]} contentStyle={tooltipStyle} />
                <Bar dataKey="net_flow" fill="#6366f1" radius={[4, 4, 0, 0]} name="Net Flow" isAnimationActive animationDuration={600} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState
              icon={BarChart2}
              title="Awaiting data"
              description="Net cash flow will appear once transactions are uploaded."
              className="h-52"
            />
          )}
        </div>
      </div>

      {/* Live Fraud Feed */}
      {user && (
        <div className="mb-8">
          <LiveFeedPanel companyId={user.company_id} />
        </div>
      )}

      {/* MoM Table */}
      {trend.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-1">Month-over-Month Growth</h2>
          <p className="text-xs text-slate-400 mb-4 font-mono">SQL: LAG() OVER (ORDER BY month) → growth %</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <caption className="sr-only">Month-over-month revenue growth table</caption>
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-700">
                  {["Month", "Inflow", "Outflow", "Net Flow", "Transactions", "MoM Growth"].map((h) => (
                    <th key={h} scope="col" className={`py-3 px-2 text-slate-500 dark:text-slate-400 font-medium text-xs ${h === "Month" ? "text-left" : "text-right"}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...trend].reverse().map((row) => (
                  <tr key={row.month} className="border-b border-slate-50 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
                    <td className="py-3 px-2 font-medium text-slate-900 dark:text-slate-100">{row.month}</td>
                    <td className="py-3 px-2 text-right text-emerald-600 dark:text-emerald-400">{formatCurrency(row.inflow)}</td>
                    <td className="py-3 px-2 text-right text-amber-600 dark:text-amber-400">{formatCurrency(row.outflow)}</td>
                    <td className={`py-3 px-2 text-right font-medium ${row.net_flow >= 0 ? "text-brand-600 dark:text-brand-400" : "text-red-600 dark:text-red-400"}`}>{formatCurrency(row.net_flow)}</td>
                    <td className="py-3 px-2 text-right text-slate-600 dark:text-slate-400">{formatNumber(row.transaction_count)}</td>
                    <td className={`py-3 px-2 text-right font-semibold ${
                      row.mom_growth_pct == null ? "text-slate-400" :
                      row.mom_growth_pct >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
                    }`}>
                      {formatPercent(row.mom_growth_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
