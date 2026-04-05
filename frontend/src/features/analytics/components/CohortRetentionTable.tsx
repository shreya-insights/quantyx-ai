import type { CohortRetentionGridResponse } from "@/types/api.types";

function cellTone(rate: number): string {
  if (rate >= 80) return "bg-emerald-500/85 text-white dark:bg-emerald-600/90";
  if (rate >= 50) return "bg-amber-400/90 text-slate-900 dark:bg-amber-500/85 dark:text-slate-900";
  if (rate >= 20) return "bg-orange-500/85 text-white";
  return "bg-red-500/85 text-white dark:bg-red-600/90";
}

interface Props {
  data: CohortRetentionGridResponse;
}

export function CohortRetentionTable({ data }: Props) {
  const { rows, cohort_months: cohortMonths, max_months: maxMonths } = data;
  const colCount = maxMonths + 1;
  const matrix = new Map<string, Map<number, number>>();
  for (const r of rows) {
    if (!matrix.has(r.cohort_month)) matrix.set(r.cohort_month, new Map());
    matrix.get(r.cohort_month)!.set(r.months_since_cohort, r.retention_rate);
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
      <table className="w-full text-xs">
        <caption className="sr-only">
          Warehouse cohort retention by month since cohort — green high retention, red churned
        </caption>
        <thead>
          <tr className="bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700">
            <th scope="col" className="py-2 px-2 text-left font-medium text-slate-600 dark:text-slate-400 sticky left-0 bg-inherit z-10">
              Cohort
            </th>
            {Array.from({ length: colCount }, (_, m) => (
              <th key={m} scope="col" className="py-2 px-1 text-center font-medium text-slate-500 dark:text-slate-400 min-w-[2.75rem]">
                M+{m}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cohortMonths.map((cm) => (
            <tr key={cm} className="border-b border-slate-100 dark:border-slate-700/60">
              <th scope="row" className="py-2 px-2 text-left font-medium text-slate-800 dark:text-slate-200 sticky left-0 bg-white dark:bg-slate-900 z-10">
                {cm}
              </th>
              {Array.from({ length: colCount }, (_, m) => {
                const rate = matrix.get(cm)?.get(m);
                return (
                  <td key={m} className="py-1 px-0.5 text-center align-middle">
                    {rate != null ? (
                      <span
                        className={`inline-flex min-h-[1.75rem] min-w-[2.5rem] items-center justify-center rounded-md text-[10px] font-semibold ${cellTone(rate)}`}
                        title={`Retention ${rate}%`}
                      >
                        {rate.toFixed(1)}%
                      </span>
                    ) : (
                      <span className="inline-block min-h-[1.75rem] min-w-[2.5rem] rounded-md bg-slate-100 dark:bg-slate-800" aria-hidden />
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
