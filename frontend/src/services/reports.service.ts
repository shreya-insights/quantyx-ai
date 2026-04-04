const BASE_URL = `${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/v1`;

const REVENUE_CSV_FILENAME = "revenue_trend.csv";
const KPI_PDF_FILENAME = "kpi_summary.pdf";

function buildReportUrl(path: string, startDate?: string, endDate?: string): string {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const query = params.toString();
  return `${BASE_URL}${path}${query ? `?${query}` : ""}`;
}

function triggerBlobDownload(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}

async function fetchWithAuth(url: string): Promise<Response> {
  const token = localStorage.getItem("access_token") ?? "";
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`Request failed (${response.status}): ${body}`);
  }
  return response;
}

export const reportsService = {
  downloadCsv: async (startDate?: string, endDate?: string): Promise<void> => {
    const url = buildReportUrl("/reports/generate/csv", startDate, endDate);
    const response = await fetchWithAuth(url);
    const blob = await response.blob();
    triggerBlobDownload(blob, REVENUE_CSV_FILENAME);
  },

  downloadPdf: async (startDate?: string, endDate?: string): Promise<void> => {
    const url = buildReportUrl("/reports/generate/pdf", startDate, endDate);
    const response = await fetchWithAuth(url);
    const blob = await response.blob();
    triggerBlobDownload(blob, KPI_PDF_FILENAME);
  },
};
