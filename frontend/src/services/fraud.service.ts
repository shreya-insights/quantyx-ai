import { api } from "@/lib/axios";
import type { FraudAlert, FraudStats, PaginatedResponse } from "@/types/api.types";

export interface AlertFilters {
  page?: number;
  page_size?: number;
  severity?: string;
  is_resolved?: boolean;
}

export const fraudService = {
  getAlerts: (filters: AlertFilters = {}) =>
    api
      .get<PaginatedResponse<FraudAlert>>("/fraud/alerts", { params: filters })
      .then((r) => r.data),

  getStats: () => api.get<FraudStats>("/fraud/stats").then((r) => r.data),

  resolveAlert: (alertId: number, note?: string) =>
    api
      .post<FraudAlert>(`/fraud/alerts/${alertId}/resolve`, { resolution_note: note })
      .then((r) => r.data),
};
