import { api } from "@/lib/axios";
import type {
  Account,
  BulkUploadResult,
  Merchant,
  PaginatedResponse,
  Transaction,
  TransactionFraudStatus,
  TransactionType,
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

export interface CreateTransactionPayload {
  account_id: number;
  merchant_id?: number;
  category_id?: number;
  amount: number;
  currency?: string;
  transaction_type: TransactionType;
  description?: string;
  transaction_date?: string;
}

export const transactionsService = {
  list: (filters: TransactionFilters = {}) =>
    api
      .get<PaginatedResponse<Transaction>>("/transactions", { params: filters })
      .then((r) => r.data),

  bulkUpload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
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

  create: (payload: CreateTransactionPayload) =>
    api.post<Transaction>("/transactions", payload).then((r) => r.data),

  getFraudStatus: (transactionId: number, jobId: string | null) =>
    api
      .get<TransactionFraudStatus>(`/transactions/${transactionId}/fraud-status`, {
        params: jobId ? { job_id: jobId } : {},
      })
      .then((r) => r.data),

  flagMerchant: (merchantId: number) =>
    api
      .post<Merchant>(`/merchants/${merchantId}/flag`)
      .then((r) => r.data),
};
