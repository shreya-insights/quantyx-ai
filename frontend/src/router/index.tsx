import { createBrowserRouter, Navigate } from "react-router-dom";
import { lazy, Suspense } from "react";
import AppShell from "@/components/layout/AppShell";
import ProtectedRoute from "@/components/common/ProtectedRoute";
import { PageSkeleton } from "@/components/ui/Skeleton";

// ─── Lazy-loaded page chunks ──────────────────────────────────────────────
const LandingPage      = lazy(() => import("@/features/auth/pages/LandingPage"));
const LoginPage        = lazy(() => import("@/features/auth/pages/LoginPage"));
const RegisterPage     = lazy(() => import("@/features/auth/pages/RegisterPage"));
const DashboardPage    = lazy(() => import("@/features/dashboard/pages/DashboardPage"));
const TransactionsPage = lazy(() => import("@/features/transactions/pages/TransactionsPage"));
const AnalyticsPage    = lazy(() => import("@/features/analytics/pages/AnalyticsPage"));
const FraudPage        = lazy(() => import("@/features/fraud/pages/FraudPage"));
const QueryLabPage     = lazy(() => import("@/features/query-lab/pages/QueryLabPage"));
const ReportsPage      = lazy(() => import("@/features/reports/pages/ReportsPage"));
const SettingsPage     = lazy(() => import("@/features/settings/pages/SettingsPage"));

const S = (el: React.ReactElement) => (
  <Suspense fallback={<PageSkeleton />}>{el}</Suspense>
);

export const router = createBrowserRouter([
  { path: "/",         element: S(<LandingPage />) },
  { path: "/login",    element: S(<LoginPage />) },
  { path: "/register", element: S(<RegisterPage />) },
  {
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      { index: true,              element: <Navigate to="/dashboard" replace /> },
      { path: "/dashboard",       element: S(<DashboardPage />) },
      { path: "/transactions",    element: S(<TransactionsPage />) },
      { path: "/analytics",       element: S(<AnalyticsPage />) },
      { path: "/fraud",           element: S(<FraudPage />) },
      { path: "/query-lab",       element: S(<QueryLabPage />) },
      { path: "/reports",         element: S(<ReportsPage />) },
      { path: "/settings",        element: S(<SettingsPage />) },
      { path: "*",                element: <Navigate to="/dashboard" replace /> },
    ],
  },
]);
