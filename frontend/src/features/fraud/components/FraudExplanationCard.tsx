import { memo, useMemo } from "react";
import { Brain, Info } from "lucide-react";
import type { MLFraudExplanation, ShapReason } from "@/types/api.types";

const MAX_BAR_WIDTH_PCT = 100;

interface Props {
  explanation: MLFraudExplanation;
  modelVersion: string | null;
}

export const FraudExplanationCard = memo(function FraudExplanationCard({
  explanation,
  modelVersion,
}: Props) {
  const maxAbs = useMemo(
    () =>
      Math.max(
        ...explanation.top_reasons.map((r) => Math.abs(r.shap_value)),
        1e-6,
      ),
    [explanation.top_reasons],
  );

  return (
    <div
      className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5 space-y-4"
      aria-label="ML fraud explanation"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Brain
            className="h-4 w-4 text-violet-500 shrink-0"
            aria-hidden="true"
          />
          <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">
            ML Fraud Analysis
          </span>
        </div>
        {modelVersion && (
          <abbr
            title={`Model trained at: ${modelVersion}`}
            className="text-xs text-slate-400 dark:text-slate-500 cursor-help no-underline border-b border-dotted border-slate-300"
          >
            v{modelVersion.slice(0, 10)}
          </abbr>
        )}
      </div>

      {/* Probability gauge */}
      <ProbabilityGauge probability={explanation.fraud_probability} />

      {/* Explanation text */}
      <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
        {explanation.explanation}
      </p>

      {/* SHAP bar chart */}
      {explanation.top_reasons.length > 0 && (
        <div className="space-y-2" aria-label="Feature contributions">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            Key signals
          </p>
          {explanation.top_reasons.map((reason) => (
            <ShapBar key={reason.feature} reason={reason} maxAbs={maxAbs} />
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 pt-1">
        <LegendDot color="bg-red-500" label="Increases risk" />
        <LegendDot color="bg-emerald-500" label="Decreases risk" />
        <span className="ml-auto flex items-center gap-1 text-xs text-slate-400 dark:text-slate-500">
          <Info className="h-3 w-3" aria-hidden="true" />
          SHAP values (EU AI Act compliant)
        </span>
      </div>
    </div>
  );
});

// ─── Sub-components ───────────────────────────────────────────────────────────

function ProbabilityGauge({ probability }: { probability: number }) {
  const pct = Math.round(probability * 100);
  const color =
    pct >= 75
      ? "text-red-600 dark:text-red-400"
      : pct >= 50
        ? "text-amber-600 dark:text-amber-400"
        : "text-emerald-600 dark:text-emerald-400";
  const trackColor =
    pct >= 75
      ? "bg-red-500"
      : pct >= 50
        ? "bg-amber-500"
        : "bg-emerald-500";

  return (
    <div aria-label={`Fraud probability: ${pct}%`}>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs text-slate-500 dark:text-slate-400">
          Fraud probability
        </span>
        <span className={`text-lg font-bold tabular-nums ${color}`}>
          {pct}%
        </span>
      </div>
      <div
        className="h-2.5 w-full rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={`h-full rounded-full transition-all duration-500 ${trackColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function ShapBar({
  reason,
  maxAbs,
}: {
  reason: ShapReason;
  maxAbs: number;
}) {
  const isRisk = reason.shap_value > 0;
  const widthPct = (Math.abs(reason.shap_value) / maxAbs) * MAX_BAR_WIDTH_PCT;

  return (
    <div className="space-y-0.5">
      <div className="flex justify-between items-center">
        <span className="text-xs text-slate-700 dark:text-slate-300 truncate max-w-[70%]">
          {reason.human_label}
        </span>
        <span
          className={`text-xs font-medium tabular-nums ${
            isRisk
              ? "text-red-600 dark:text-red-400"
              : "text-emerald-600 dark:text-emerald-400"
          }`}
        >
          {isRisk ? "+" : ""}
          {reason.shap_value.toFixed(4)}
        </span>
      </div>
      <div
        className="h-1.5 w-full rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden"
        aria-label={`${reason.human_label}: ${reason.direction}`}
      >
        <div
          className={`h-full rounded-full transition-all duration-300 ${
            isRisk ? "bg-red-500" : "bg-emerald-500"
          }`}
          style={{ width: `${widthPct}%` }}
        />
      </div>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
      <span
        className={`inline-block h-2 w-2 rounded-full ${color}`}
        aria-hidden="true"
      />
      {label}
    </span>
  );
}

/** Shown inside the table row when rule_metadata is null (rules-only alert). */
export function RulesOnlyBadge() {
  return (
    <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500 py-2">
      <Info className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      Rule-based detection — ML model not yet trained
    </div>
  );
}
