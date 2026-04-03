import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { ROUTES } from "@/utils/constants";

const BASE_URL = `${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/v1`;

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// ─── Request interceptor — attach JWT ─────────────────────────────────────
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem("access_token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ─── Response interceptor — handle 401 ──────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      // Clear Zustand store state that was persisted
      localStorage.removeItem("quantyx-auth");
      window.location.href = ROUTES.LOGIN;
    }
    return Promise.reject(error);
  }
);
