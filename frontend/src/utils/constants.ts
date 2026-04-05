export const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800 border border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800",
  high:     "bg-orange-100 text-orange-800 border border-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-800",
  medium:   "bg-yellow-100 text-yellow-800 border border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-800",
  low:      "bg-blue-100 text-blue-800 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800",
};

export const STATUS_COLORS: Record<string, string> = {
  completed: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
  pending:   "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  failed:    "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  reversed:  "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
};

export const TX_TYPE_COLORS: Record<string, string> = {
  debit:    "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400",
  credit:   "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400",
  transfer: "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400",
  refund:   "bg-purple-50 text-purple-700 dark:bg-purple-900/20 dark:text-purple-400",
};

export const CHART_COLORS = [
  "#3b82f6", "#8b5cf6", "#10b981", "#f59e0b",
  "#ef4444", "#06b6d4", "#f97316", "#84cc16",
  "#ec4899", "#14b8a6",
];

export const SEGMENT_COLORS: Record<string, string> = {
  "Champions":          "#1d4ed8",
  "Loyal Customers":    "#7c3aed",
  "Potential Loyalists":"#059669",
  "Recent Customers":   "#0891b2",
  "At Risk":            "#d97706",
  "Big Spenders":       "#9333ea",
  "Lost Customers":     "#dc2626",
};

export const ROUTES = {
  HOME:          "/",
  LOGIN:         "/login",
  REGISTER:      "/register",
  ONBOARDING:    "/onboarding",
  ACCEPT_INVITE: "/accept-invite",
  DASHBOARD:     "/dashboard",
  TRANSACTIONS:  "/transactions",
  ANALYTICS:     "/analytics",
  FRAUD:         "/fraud",
  QUERY_LAB:     "/query-lab",
  REPORTS:       "/reports",
  SETTINGS:      "/settings",
  AI_ANALYST:    "/ai-analyst",
} as const;
