import { memo } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2, Shield } from "lucide-react";
import { transactionsService } from "@/services/transactions.service";
import type { TransactionFraudPollStatus } from "@/types/api.types";

const POLL_MS = 2000;

function shouldPoll(status: TransactionFraudPollStatus | undefined): boolean {
  return status === "pending" || status === "analyzing";
}

export const FraudStatusBadge = memo(function FraudStatusBadge({
  jobId,
  transactionId,
}: {
  jobId: string | null;
  transactionId: number;
}) {
  const { data, isError, isLoading } = useQuery({
    queryKey: ["fraud-status", transactionId, jobId],
    queryFn: () => transactionsService.getFraudStatus(transactionId, jobId),
    refetchInterval: (query) =>
      shouldPoll(query.state.data?.status) ? POLL_MS : false,
  });

  if (isError) {
    return (
      <span
        className="text-xs text-amber-600 dark:text-amber-400"
        role="status"
        aria-live="polite"
      >
        Check unavailable, contact support
      </span>
    );
  }

  if (isLoading && !data) {
    return (
      <span
        className="inline-flex items-center gap-1 text-xs text-slate-400"
        aria-hidden="true"
      >
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        …
      </span>
    );
  }

  const status = data?.status;

  if (status === "flagged" && data?.alert) {
    const label = `Fraud: ${data.alert.severity}`;
    return (
      <span
        className="inline-flex items-center gap-1 text-xs text-red-600 dark:text-red-400"
        title={data.alert.description ?? label}
        aria-label={label}
      >
        <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span className="rounded bg-red-100 dark:bg-red-900/40 px-1.5 py-0.5 font-medium capitalize">
          {data.alert.severity}
        </span>
      </span>
    );
  }

  if (status === "unavailable") {
    return (
      <span
        className="text-xs text-amber-600 dark:text-amber-400"
        role="status"
        aria-live="polite"
        title="Celery task failed, Redis unreachable, or worker not running."
      >
        Check unavailable, contact support
      </span>
    );
  }

  if (status === "not_analyzed") {
    return (
      <span
        className="text-xs text-slate-500 dark:text-slate-400"
        role="status"
        aria-live="polite"
        title="Bulk CSV rows are not queued for fraud analysis. Create a transaction via API or extend ingestion."
      >
        Not scanned
      </span>
    );
  }

  if (status === "clear") {
    return (
      <span
        className="inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400"
        aria-label="No fraud alerts"
      >
        <Shield className="h-3.5 w-3.5" aria-hidden="true" />
        Clear
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1 text-xs text-amber-700 dark:text-amber-300"
      aria-busy="true"
      aria-label="Fraud analysis in progress"
    >
      <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
      Analyzing…
    </span>
  );
});
