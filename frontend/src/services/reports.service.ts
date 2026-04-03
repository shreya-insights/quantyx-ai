const BASE_URL = `${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/v1`;

export const reportsService = {
  getCsvUrl: (startDate?: string, endDate?: string) => {
    const token = localStorage.getItem("access_token") ?? "";
    const params = new URLSearchParams();
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    // Token is passed as query param for file download links
    params.set("token", token);
    return `${BASE_URL}/reports/generate/csv?${params.toString()}`;
  },

  getPdfUrl: (startDate?: string, endDate?: string) => {
    const token = localStorage.getItem("access_token") ?? "";
    const params = new URLSearchParams();
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    params.set("token", token);
    return `${BASE_URL}/reports/generate/pdf?${params.toString()}`;
  },
};
