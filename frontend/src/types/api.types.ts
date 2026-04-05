// ─── Common ─────────────────────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  error_code: string;
  detail: string;
}

// ─── Auth ────────────────────────────────────────────────────────────────────
export type UserRole = "admin" | "analyst" | "viewer";

export interface User {
  id: number;
  company_id: number;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ─── Transactions ────────────────────────────────────────────────────────────
export type TransactionType = "debit" | "credit" | "transfer" | "refund";
export type TransactionStatus = "pending" | "completed" | "failed" | "reversed";

export interface Transaction {
  id: number;
  company_id: number;
  account_id: number;
  merchant_id: number | null;
  category_id: number | null;
  transaction_ref: string;
  amount: number;
  currency: string;
  transaction_type: TransactionType;
  status: TransactionStatus;
  description: string | null;
  transaction_date: string;
  created_at: string;
  merchant_name: string | null;
  category_name: string | null;
  account_number: string | null;
  fraud_check_job_id?: string | null;
  fraud_check_status?: string | null;
}

export interface Account {
  id: number;
  company_id: number;
  user_id: number | null;
  account_number: string;
  account_type: string;
  balance: number;
  currency: string;
  is_active: boolean;
  created_at: string;
}

export interface Merchant {
  id: number;
  company_id: number;
  name: string;
  category_code: string | null;
  country: string | null;
  city: string | null;
  is_flagged: boolean;
  created_at: string;
}

export interface BulkUploadResult {
  total_rows: number;
  inserted: number;
  failed: number;
  errors: string[];
}

// ─── Analytics ───────────────────────────────────────────────────────────────
export interface RevenueTrendPoint {
  month: string;
  inflow: number;
  outflow: number;
  net_flow: number;
  transaction_count: number;
  avg_transaction: number;
  mom_growth_pct: number | null;
}

export interface RevenueTrendResponse {
  data: RevenueTrendPoint[];
  period_months: number;
  total_inflow: number;
  total_outflow: number;
  avg_monthly_inflow: number;
}

export interface RFMCustomer {
  account_id: number;
  account_number: string | null;
  user_email: string | null;
  user_name: string | null;
  recency_days: number;
  frequency: number;
  monetary_value: number;
  r_score: number;
  f_score: number;
  m_score: number;
  segment: string;
}

export interface RFMSegmentSummary {
  segment: string;
  customer_count: number;
  avg_recency_days: number;
  avg_frequency: number;
  avg_monetary_value: number;
  total_revenue: number;
  pct_of_total: number;
}

export interface RFMResponse {
  segments: RFMSegmentSummary[];
  customers: RFMCustomer[];
  analysis_date: string;
  total_customers: number;
}

export interface CohortRetentionRow {
  cohort_month: string;
  cohort_size: number;
  period_0: number;
  period_1: number | null;
  period_2: number | null;
  period_3: number | null;
  period_6: number | null;
  period_12: number | null;
}

export interface CohortResponse {
  data: CohortRetentionRow[];
  periods_analyzed: number;
}

/** Pre-aggregated warehouse cohort grid (nightly ETL). */
export interface CohortRetentionCell {
  cohort_month: string;
  months_since_cohort: number;
  retention_rate: number;
  user_count: number;
  retained_count: number;
}

export interface CohortRetentionGridResponse {
  rows: CohortRetentionCell[];
  cohort_months: string[];
  max_months: number;
}

export type LTVSegmentName = "high" | "medium" | "low";

export interface LTVSegment {
  segment: LTVSegmentName;
  user_count: number;
  pct_of_total: number;
  avg_spend: number;
}

export interface LTVSegmentsResponse {
  segments: LTVSegment[];
  total_users: number;
}

export interface HeatmapCell {
  day_of_week: number;
  hour_of_day: number;
  avg_count: number;
  avg_amount: number;
  fraud_rate: number;
}

export interface HeatmapResponse {
  cells: HeatmapCell[];
}

export interface MerchantRanking {
  rank: number;
  merchant_id: number;
  merchant_name: string;
  category_code: string | null;
  total_revenue: number;
  transaction_count: number;
  avg_transaction: number;
  revenue_share_pct: number;
  rank_in_category: number;
}

export interface MerchantRankingResponse {
  data: MerchantRanking[];
  total_merchants: number;
  analysis_period_days: number;
}

export interface KpiSummary {
  period_start: string;
  period_end: string;
  total_transactions: number;
  total_volume: number;
  total_inflow: number;
  total_outflow: number;
  unique_customers: number;
  unique_merchants: number;
  avg_transaction_value: number;
  fraud_alert_count: number;
  fraud_alert_rate_pct: number;
  top_category: string | null;
  mom_volume_growth_pct: number | null;
  active_accounts: number;
}

export interface SpendingByCategory {
  category_name: string;
  category_code: string;
  total_amount: number;
  transaction_count: number;
  pct_of_total: number;
}

// ─── Fraud ───────────────────────────────────────────────────────────────────
export type AlertSeverity = "low" | "medium" | "high" | "critical";
export type AlertType =
  | "rapid_transactions"
  | "unusual_amount"
  | "location_anomaly"
  | "new_device"
  | "velocity_breach"
  | "duplicate_transaction"
  | "night_pattern"
  | "ml_fraud_score";

export interface ShapReason {
  feature: string;
  shap_value: number;
  human_label: string;
  direction: "increases fraud risk" | "decreases fraud risk";
}

export interface MLFraudExplanation {
  fraud_probability: number;
  top_reasons: ShapReason[];
  explanation: string;
}

export interface FraudAlert {
  id: number;
  company_id: number;
  transaction_id: number;
  alert_type: AlertType;
  severity: AlertSeverity;
  confidence_score: number | null;
  description: string | null;
  is_resolved: boolean;
  resolved_by: number | null;
  resolved_at: string | null;
  rule_metadata: string | null;
  model_version: string | null;
  created_at: string;
  ml_explanation: MLFraudExplanation | null;
  transaction_amount: number | null;
  transaction_ref: string | null;
  transaction_date: string | null;
  account_number: string | null;
  user_email: string | null;
}

export type TransactionFraudPollStatus =
  | "pending"
  | "analyzing"
  | "clear"
  | "flagged"
  | "unavailable"
  | "not_analyzed";

export interface TransactionFraudStatus {
  status: TransactionFraudPollStatus;
  job_id: string | null;
  alert: FraudAlert | null;
}

export interface FraudStats {
  total_alerts: number;
  open_alerts: number;
  resolved_alerts: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  alerts_by_type: Record<string, number>;
  resolution_rate_pct: number;
  avg_resolution_time_hours: number | null;
  recent_trend: Array<{ date: string; count: number }>;
}

// ─── Query Lab ───────────────────────────────────────────────────────────────
export interface QueryResult {
  columns: string[];
  rows: unknown[][];
  row_count: number;
  execution_time_ms: number;
  truncated: boolean;
}

export interface QueryTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  query_text: string;
  tags: string[];
}

export interface SavedQuery {
  id: number;
  name: string;
  description: string | null;
  query_text: string;
  is_public: boolean;
  execution_count: number;
  last_executed_at: string | null;
  created_at: string;
  user_email: string | null;
}

// ─── WebSocket Events ────────────────────────────────────────────────────────
export type WsConnectionStatus = "connecting" | "connected" | "reconnecting";

export interface WsFraudAlertEvent {
  type: "fraud_alert";
  data: FraudAlert;
  timestamp: string;
}

export interface WsTransactionEvent {
  type: "transaction";
  data: Transaction;
  timestamp: string;
}

export interface WsPingEvent {
  type: "ping";
}

export type WsEvent = WsFraudAlertEvent | WsTransactionEvent | WsPingEvent;

// ─── Subscriptions ───────────────────────────────────────────────────────────
export interface PlanDetails {
  name: string;
  monthly_price: number;
  annual_price: number;
  user_limit: number | null;
  transaction_limit: number | null;
  api_calls_limit: number | null;
  features: string[];
}

export interface Subscription {
  id: number;
  company_id: number;
  plan_name: string;
  status: string;
  billing_cycle: string;
  amount: number;
  currency: string;
  starts_at: string;
  ends_at: string | null;
  api_calls_limit: number | null;
  api_calls_used: number;
  created_at: string;
}

export interface DailyUsage {
  date: string;
  calls: number;
}

export interface UsageStats {
  plan_name: string;
  api_calls_used: number;
  api_calls_limit: number | null;
  api_calls_remaining: number | null;
  usage_pct: number | null;
  transaction_count_this_month: number;
  transaction_limit: number | null;
  current_month_calls: number;
  reset_date: string;
  daily_breakdown: DailyUsage[];
}
