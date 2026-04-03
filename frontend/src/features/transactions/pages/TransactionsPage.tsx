import { useRef, useState } from "react";
import { Upload, ChevronLeft, ChevronRight, X, CheckCircle2, CreditCard } from "lucide-react";
import { useTransactions, useBulkUpload } from "../hooks/useTransactions";
import { Button, Badge, TableRowSkeleton } from "@/components/ui";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { formatCurrency, formatDateTime } from "@/utils/format";
import { STATUS_COLORS, TX_TYPE_COLORS } from "@/utils/constants";
import type { TransactionFilters } from "@/services/transactions.service";

const PAGE_SIZE = 20;

export default function TransactionsPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [filters, setFilters] = useState<TransactionFilters>({ page: 1, page_size: PAGE_SIZE });

  const { data, isLoading } = useTransactions(filters);
  const uploadMutation = useBulkUpload();

  const transactions = data?.data ?? [];
  const total        = data?.total ?? 0;
  const totalPages   = data?.total_pages ?? 1;
  const currentPage  = filters.page ?? 1;

  const updateFilter = <K extends keyof TransactionFilters>(key: K, value: TransactionFilters[K]) => {
    setFilters((prev) => {
      const next = { ...prev, [key]: value };
      if (key !== "page") {
        next.page = 1;
      }
      return next;
    });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadMutation.mutate(file);
      e.target.value = "";
    }
  };

  return (
    <div className="p-6 lg:p-8">
      <PageHeader
        title="Transactions"
        subtitle={`${total.toLocaleString()} total transactions`}
        action={
          <>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              id="csv-upload"
              aria-label="Upload CSV file"
              className="sr-only"
              onChange={handleFileChange}
            />
            <Button
              onClick={() => fileRef.current?.click()}
              loading={uploadMutation.isPending}
              leftIcon={<Upload size={14} aria-hidden="true" />}
              size="sm"
            >
              Upload CSV
            </Button>
          </>
        }
      />

      {/* Upload feedback */}
      {uploadMutation.isSuccess && (
        <div className="mb-4 p-4 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 text-sm text-emerald-700 dark:text-emerald-300 flex items-start gap-2">
          <CheckCircle2 size={16} className="flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            Uploaded: {uploadMutation.data.inserted} inserted, {uploadMutation.data.failed} failed.
            {uploadMutation.data.errors.length > 0 && (
              <ul className="mt-1 list-disc list-inside text-xs">
                {uploadMutation.data.errors.slice(0, 5).map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            )}
          </div>
        </div>
      )}

      {uploadMutation.isError && (
        <div className="mb-4 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">
          Upload failed. Please try again.
        </div>
      )}

      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-4 flex flex-wrap gap-3 items-center">
        <select
          value={filters.transaction_type ?? ""}
          onChange={(e) => updateFilter("transaction_type", e.target.value || undefined)}
          aria-label="Filter by transaction type"
          className="border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">All Types</option>
          <option value="debit">Debit</option>
          <option value="credit">Credit</option>
          <option value="transfer">Transfer</option>
          <option value="refund">Refund</option>
        </select>

        <select
          value={filters.status ?? ""}
          onChange={(e) => updateFilter("status", e.target.value || undefined)}
          aria-label="Filter by status"
          className="border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">All Statuses</option>
          <option value="completed">Completed</option>
          <option value="pending">Pending</option>
          <option value="failed">Failed</option>
          <option value="reversed">Reversed</option>
        </select>

        <label className="sr-only" htmlFor="tx-start-date">Start date</label>
        <input
          id="tx-start-date"
          type="date"
          value={filters.start_date ?? ""}
          onChange={(e) => updateFilter("start_date", e.target.value || undefined)}
          className="border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <label className="sr-only" htmlFor="tx-end-date">End date</label>
        <input
          id="tx-end-date"
          type="date"
          value={filters.end_date ?? ""}
          onChange={(e) => updateFilter("end_date", e.target.value || undefined)}
          className="border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />

        {(filters.transaction_type || filters.status || filters.start_date || filters.end_date) && (
          <button
            onClick={() => setFilters({ page: 1, page_size: PAGE_SIZE })}
            aria-label="Clear filters"
            className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
          >
            <X size={14} aria-hidden="true" /> Clear
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Transactions table</caption>
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700">
                {["Reference", "Account", "Merchant", "Amount", "Type", "Status", "Date"].map((h, i) => (
                  <th key={h} scope="col" className={`py-3 px-4 font-medium text-slate-500 dark:text-slate-400 text-xs ${i > 2 ? "text-center" : "text-left"}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 10 }).map((_, i) => <TableRowSkeleton key={i} cols={7} />)
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={7}>
                    <EmptyState
                      icon={Upload}
                      title="No transactions yet"
                      description="Upload a CSV to start analyzing your finances. Supports standard bank export formats."
                      action={
                        <button
                          onClick={() => fileRef.current?.click()}
                          className="inline-flex items-center gap-1.5 text-sm text-brand-600 dark:text-brand-400 hover:underline font-medium"
                        >
                          <Upload size={14} aria-hidden="true" /> Upload your first CSV
                        </button>
                      }
                    />
                  </td>
                </tr>
              ) : (
                transactions.map((tx) => (
                  <tr key={tx.id} className="border-b border-slate-50 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
                    <td className="py-3 px-4 font-mono text-xs text-brand-600 dark:text-brand-400">{tx.transaction_ref}</td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400 text-xs">{tx.account_number ?? "—"}</td>
                    <td className="py-3 px-4 text-slate-700 dark:text-slate-300">{tx.merchant_name ?? "—"}</td>
                    <td className={`py-3 px-4 text-center font-semibold ${tx.transaction_type === "credit" ? "text-emerald-600 dark:text-emerald-400" : "text-slate-900 dark:text-slate-100"}`}>
                      {tx.transaction_type === "credit" ? "+" : tx.transaction_type === "debit" ? "−" : ""}
                      {formatCurrency(tx.amount, tx.currency)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${TX_TYPE_COLORS[tx.transaction_type] ?? ""}`}>
                        {tx.transaction_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Badge variant={
                        tx.status === "completed" ? "success" :
                        tx.status === "pending"   ? "warning" :
                        tx.status === "failed"    ? "danger"  : "default"
                      }>
                        {tx.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-slate-400 dark:text-slate-500 text-xs whitespace-nowrap">{formatDateTime(tx.transaction_date)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-700 flex items-center justify-between">
            <span className="text-sm text-slate-400">Page {currentPage} of {totalPages} pages · {total.toLocaleString()} records total</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => updateFilter("page", currentPage - 1)} disabled={currentPage === 1} leftIcon={<ChevronLeft size={14} aria-hidden="true" />}>
                Prev
              </Button>
              <Button variant="outline" size="sm" onClick={() => updateFilter("page", currentPage + 1)} disabled={currentPage >= totalPages} rightIcon={<ChevronRight size={14} aria-hidden="true" />}>
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
