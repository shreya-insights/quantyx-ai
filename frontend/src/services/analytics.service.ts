import { api } from "@/lib/axios";
import type {
  CohortResponse,
  KpiSummary,
  MerchantRankingResponse,
  RFMResponse,
  RevenueTrendResponse,
  SpendingByCategory,
} from "@/types/api.types";

interface TransactionFrequency {
  period: string;
  hour_of_day: number;
  day_of_week: string;
  transaction_count: number;
  total_amount: number;
  avg_amount: number;
}

export const analyticsService = {
  getKpiSummary: (startDate?: string, endDate?: string) =>
    api
      .get<KpiSummary>("/analytics/kpi-summary", {
        params: { start_date: startDate, end_date: endDate },
      })
      .then((r) => r.data),

  getRevenueTrends: (months = 12) =>
    api
      .get<RevenueTrendResponse>("/analytics/revenue-trends", { params: { months } })
      .then((r) => r.data),

  getCustomerSegmentation: () =>
    api.get<RFMResponse>("/analytics/customer-segmentation").then((r) => r.data),

  getCohortRetention: () =>
    api.get<CohortResponse>("/analytics/cohort").then((r) => r.data),

  getTopMerchants: (days = 30, topN = 20) =>
    api
      .get<MerchantRankingResponse>("/analytics/top-merchants", {
        params: { days, top_n: topN },
      })
      .then((r) => r.data),

  getSpendingByCategory: (days = 30) =>
    api
      .get<SpendingByCategory[]>("/analytics/spending-by-category", { params: { days } })
      .then((r) => r.data),

  getTransactionHeatmap: (days = 90) =>
    api
      .get<TransactionFrequency[]>("/analytics/transaction-heatmap", { params: { days } })
      .then((r) => r.data),
};
