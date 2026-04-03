import { api } from "@/lib/axios";
import type { Account, BulkUploadResult, Merchant, PaginatedResponse, Transaction } from "@/types/api.types";

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
    return api
      .post<BulkUploadResult>("/transactions/bulk-upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
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
};
