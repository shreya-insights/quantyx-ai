import { useState } from "react";
import { BarChart2, FileDown, Download } from "lucide-react";
import { reportsService } from "@/services/reports.service";
import { Button } from "@/components/ui";
import { PageHeader } from "@/components/common/PageHeader";

function toDate(d: Date) {
  return d.toISOString().split("T")[0];
}

const today         = toDate(new Date());
const thirtyDaysAgo = toDate(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000));

type DownloadType = "csv" | "pdf";

export default function ReportsPage() {
  const [startDate, setStartDate]   = useState(thirtyDaysAgo);
  const [endDate, setEndDate]       = useState(today);
  const [loadingCsv, setLoadingCsv] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [error, setError]           = useState<string | null>(null);

  const handleDownload = async (type: DownloadType) => {
    const setLoading = type === "csv" ? setLoadingCsv : setLoadingPdf;
    setError(null);
    setLoading(true);
    try {
      if (type === "csv") {
        await reportsService.downloadCsv(startDate, endDate);
      } else {
        await reportsService.downloadPdf(startDate, endDate);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Download failed. Please try again.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 lg:p-8">
      <PageHeader title="Reports" subtitle="Export KPI and revenue reports as CSV or PDF" />

      <div className="max-w-xl space-y-4">
        {/* Date range */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="font-semibold text-slate-900 dark:text-slate-100 mb-4">Report Period</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="report-start" className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1.5">
                Start Date
              </label>
              <input
                id="report-start"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div>
              <label htmlFor="report-end" className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1.5">
                End Date
              </label>
              <input
                id="report-end"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-400">
            {error}
          </div>
        )}

        {/* CSV Report */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
              <BarChart2 size={20} className="text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-slate-900 dark:text-slate-100">Revenue Trend Report (CSV)</h3>
              <p className="text-sm text-slate-400 mt-0.5">Monthly inflow, outflow, net flow, and MoM growth — ready for Excel or Power BI</p>
              <Button
                variant="secondary"
                size="sm"
                className="mt-3"
                onClick={() => handleDownload("csv")}
                disabled={loadingCsv}
                aria-label="Download Revenue Trend CSV report"
                leftIcon={<Download size={14} aria-hidden="true" />}
              >
                {loadingCsv ? "Downloading…" : "Download CSV"}
              </Button>
            </div>
          </div>
        </div>

        {/* PDF Report */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
              <FileDown size={20} className="text-red-600 dark:text-red-400" aria-hidden="true" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-slate-900 dark:text-slate-100">KPI Summary Report (PDF)</h3>
              <p className="text-sm text-slate-400 mt-0.5">Formatted PDF with total volume, fraud rate, customer count, and transaction metrics</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() => handleDownload("pdf")}
                disabled={loadingPdf}
                aria-label="Download KPI Summary PDF report"
                leftIcon={<FileDown size={14} aria-hidden="true" />}
              >
                {loadingPdf ? "Downloading…" : "Download PDF"}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
