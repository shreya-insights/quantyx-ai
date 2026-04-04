import { api } from "@/lib/axios";
import type {
  Account,
  BulkUploadResult,
  Merchant,
  PaginatedResponse,
  Transaction,
  TransactionFraudStatus,
} from "@/types/api.types";

export interface TransactionFilters {
  page?: number;
  page_size?: number;
  transaction_type?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  account_id?: number;
  min_amount?: number;
  max_amount?: number;
}

export const transactionsService = {
  list: (filters: TransactionFilters = {}) =>
    api
      .get<PaginatedResponse<Transaction>>("/transactions", { params: filters })
      .then((r) => r.data),

  bulkUpload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    // Do not set Content-Type manually — multipart needs a boundary; axios strips
    // the default application/json header when data is FormData.
    return api.post<BulkUploadResult>("/transactions/bulk-upload", form).then((r) => r.data);
  },

  listAccounts: () => api.get<Account[]>("/accounts").then((r) => r.data),

  createAccount: (payload: {
    account_number: string;
    account_type: string;
    balance?: number;
    currency?: string;
    user_id?: number;
  }) => api.post<Account>("/accounts", payload).then((r) => r.data),

  listMerchants: () => api.get<Merchant[]>("/merchants").then((r) => r.data),

  getFraudStatus: (transactionId: number, jobId: string | null) =>
    api
      .get<TransactionFraudStatus>(`/transactions/${transactionId}/fraud-status`, {
        params: jobId ? { job_id: jobId } : {},
      })
      .then((r) => r.data),
};
