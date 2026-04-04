import { useState } from "react";
import { Brain, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, ShieldCheck } from "lucide-react";
import { useFraudAlerts, useFraudStats, useResolveAlert } from "../hooks/useFraud";
import { FraudExplanationCard, RulesOnlyBadge } from "../components/FraudExplanationCard";
import { Button, TableRowSkeleton } from "@/components/ui";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { formatCurrency, formatDateTime } from "@/utils/format";
import { SEVERITY_COLORS } from "@/utils/constants";

const ALERT_TYPE_LABELS: Record<string, string> = {
  rapid_transactions:    "Rapid Transactions",
  unusual_amount:        "Unusual Amount",
  location_anomaly:      "Location Anomaly",
  new_device:            "New Device",
  velocity_breach:       "Velocity Breach",
  duplicate_transaction: "Duplicate",
  night_pattern:         "Night Pattern",
  ml_fraud_score:        "ML Score",
};

export default function FraudPage() {
  const [page, setPage]             = useState(1);
  const [severity, setSeverity]     = useState("");
  const [isResolved, setIsResolved] = useState<boolean | undefined>(undefined);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const alertsQuery     = useFraudAlerts({ page, page_size: 20, severity: severity || undefined, is_resolved: isResolved });
  const statsQuery      = useFraudStats();
  const resolveMutation = useResolveAlert();

  const alerts     = alertsQuery.data?.data ?? [];
  const total      = alertsQuery.data?.total ?? 0;
  const totalPages = alertsQuery.data?.total_pages ?? 1;
  const stats      = statsQuery.data;

  const toggleExpand = (id: number) =>
    setExpandedId((prev) => (prev === id ? null : id));

  return (
    <div className="p-6 lg:p-8">
      <PageHeader
        title="Fraud Monitor"
        subtitle="Rule-based + ML detection with SHAP explainability"
      />

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">Total Alerts</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{stats.total_alerts}</p>
          </div>
          <div className="bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-100 dark:border-red-900/30 p-5">
            <p className="text-xs text-red-500 mb-1">Open Alerts</p>
            <p className="text-2xl font-bold text-red-700 dark:text-red-400">{stats.open_alerts}</p>
          </div>
          <div className="bg-emerald-50 dark:bg-emerald-900/10 rounded-xl border border-emerald-100 dark:border-emerald-900/30 p-5">
            <p className="text-xs text-emerald-600 mb-1">Resolved</p>
            <p className="text-2xl font-bold text-emerald-700 dark:text-emerald-400">{stats.resolved_alerts}</p>
          </div>
          <div className="bg-amber-50 dark:bg-amber-900/10 rounded-xl border border-amber-100 dark:border-amber-900/30 p-5">
            <p className="text-xs text-amber-500 mb-1">Resolution Rate</p>
            <p className="text-2xl font-bold text-amber-700 dark:text-amber-400">{stats.resolution_rate_pct ?? 0}%</p>
          </div>
        </div>
      )}

      {/* Severity breakdown */}
      {stats && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-4 flex flex-wrap gap-3 items-center">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Severity:</span>
          {[
            { label: "Critical", count: stats.critical_count, cls: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300" },
            { label: "High",     count: stats.high_count,     cls: "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300" },
            { label: "Medium",   count: stats.medium_count,   cls: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300" },
            { label: "Low",      count: stats.low_count,      cls: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300" },
          ].map((s) => (
            <span key={s.label} className={`text-xs px-3 py-1 rounded-full font-medium ${s.cls}`}>
              {s.label}: {s.count}
            </span>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-4 flex flex-wrap gap-3 items-center">
        <select
          value={severity}
          onChange={(e) => { setSeverity(e.target.value); setPage(1); }}
          aria-label="Filter by severity"
          className="border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <select
          value={isResolved === undefined ? "" : String(isResolved)}
          onChange={(e) => {
            setIsResolved(e.target.value === "" ? undefined : e.target.value === "true");
            setPage(1);
          }}
          aria-label="Filter by resolution status"
          className="border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">All</option>
          <option value="false">Open Only</option>
          <option value="true">Resolved Only</option>
        </select>

        <span className="text-sm text-slate-400">{total} alerts</span>
      </div>

      {/* Alerts Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Fraud alerts table</caption>
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700">
                <th scope="col" className="py-3 px-4 w-8" aria-label="Expand" />
                {["Type", "Severity", "Amount", "Account", "Description", "Confidence", "Detected", "Action"].map((h) => (
                  <th key={h} scope="col" className="py-3 px-4 text-left text-xs font-medium text-slate-500 dark:text-slate-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {alertsQuery.isLoading
                ? Array.from({ length: 8 }).map((_, i) => <TableRowSkeleton key={i} cols={9} />)
                : alerts.length === 0
                  ? (
                    <tr>
                      <td colSpan={9}>
                        <EmptyState
                          icon={ShieldCheck}
                          title="All clear — no alerts"
                          description="Alerts appear automatically when suspicious patterns are detected."
                        />
                      </td>
                    </tr>
                  )
                  : alerts.map((alert) => {
                    const isExpanded = expandedId === alert.id;
                    const isML = alert.alert_type === "ml_fraud_score";

                    return [
                      <tr
                        key={alert.id}
                        className="border-b border-slate-50 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30 cursor-pointer"
                        onClick={() => toggleExpand(alert.id)}
                        aria-expanded={isExpanded}
                      >
                        {/* Expand toggle */}
                        <td className="py-3 px-3">
                          <button
                            aria-label={isExpanded ? "Collapse explanation" : "Expand explanation"}
                            className="text-slate-400 hover:text-violet-500 transition-colors"
                            onClick={(e) => { e.stopPropagation(); toggleExpand(alert.id); }}
                          >
                            {isExpanded
                              ? <ChevronUp size={14} aria-hidden="true" />
                              : <ChevronDown size={14} aria-hidden="true" />}
                          </button>
                        </td>
                        <td className="py-3 px-4 font-medium text-slate-700 dark:text-slate-300">
                          <span className="flex items-center gap-1.5">
                            {isML && (
                              <Brain
                                size={13}
                                className="text-violet-500 shrink-0"
                                aria-label="ML detection"
                              />
                            )}
                            {ALERT_TYPE_LABELS[alert.alert_type] ?? alert.alert_type}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${SEVERITY_COLORS[alert.severity] ?? ""}`}>
                            {alert.severity}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-medium text-slate-900 dark:text-slate-100">
                          {alert.transaction_amount ? formatCurrency(alert.transaction_amount) : "—"}
                        </td>
                        <td className="py-3 px-4 text-slate-500 dark:text-slate-400 text-xs">
                          {alert.account_number ?? "—"}
                        </td>
                        <td className="py-3 px-4 text-slate-600 dark:text-slate-400 text-xs max-w-xs truncate">
                          {alert.description ?? "—"}
                        </td>
                        <td className="py-3 px-4">
                          {alert.confidence_score != null ? (
                            <div className="flex items-center gap-1.5">
                              <div className="w-12 bg-slate-100 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden">
                                <div
                                  className={`h-1.5 rounded-full ${alert.confidence_score >= 80 ? "bg-red-500" : alert.confidence_score >= 60 ? "bg-orange-500" : "bg-amber-500"}`}
                                  style={{ width: `${alert.confidence_score}%` }}
                                />
                              </div>
                              <span className="text-xs text-slate-400">{alert.confidence_score}%</span>
                            </div>
                          ) : "—"}
                        </td>
                        <td className="py-3 px-4 text-slate-400 dark:text-slate-500 text-xs whitespace-nowrap">
                          {formatDateTime(alert.created_at)}
                        </td>
                        <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                          {alert.is_resolved ? (
                            <span className="inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                              <ShieldCheck size={13} aria-hidden="true" /> Resolved
                            </span>
                          ) : (
                            <Button
                              variant="outline"
                              size="sm"
                              loading={resolveMutation.isPending && resolveMutation.variables?.id === alert.id}
                              onClick={() => resolveMutation.mutate({ id: alert.id, note: "Resolved via dashboard" })}
                            >
                              Resolve
                            </Button>
                          )}
                        </td>
                      </tr>,

                      /* Expandable explanation row */
                      isExpanded && (
                        <tr key={`${alert.id}-detail`} className="bg-slate-50/60 dark:bg-slate-900/30">
                          <td />
                          <td colSpan={8} className="px-4 pb-4 pt-2">
                            {alert.ml_explanation ? (
                              <FraudExplanationCard
                                explanation={alert.ml_explanation}
                                modelVersion={alert.model_version}
                              />
                            ) : (
                              <RulesOnlyBadge />
                            )}
                          </td>
                        </tr>
                      ),
                    ];
                  })
              }
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-700 flex items-center justify-between">
            <span className="text-sm text-slate-400">Page {page} of {totalPages}</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setPage(page - 1)} disabled={page === 1} leftIcon={<ChevronLeft size={14} aria-hidden="true" />}>
                Prev
              </Button>
              <Button variant="outline" size="sm" onClick={() => setPage(page + 1)} disabled={page >= totalPages} rightIcon={<ChevronRight size={14} aria-hidden="true" />}>
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
