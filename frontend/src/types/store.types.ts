// ─── Notification ────────────────────────────────────────────────────────────

export interface Notification {
  id: string;
  type: "fraud_alert" | "system" | "success" | "error" | "info";
  title: string;
  message: string;
  severity?: "low" | "medium" | "high" | "critical";
  transactionId?: number;
  createdAt: string;
  read: boolean;
  action?: { label: string; href: string };
}

// ─── Store shapes ─────────────────────────────────────────────────────────────

export interface UIStore {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (v: boolean) => void;

  activeModal: string | null;
  openModal: (id: string) => void;
  closeModal: () => void;

  pageLoading: boolean;
  setPageLoading: (v: boolean) => void;

  pageSize: number;
  setPageSize: (n: number) => void;
}

export interface TransactionFilters {
  search: string;
  status: string | null;
  type: string | null;
  dateFrom: string | null;
  dateTo: string | null;
  accountId: number | null;
  merchantId: number | null;
}

export interface FraudFilters {
  severity: string | null;
  alertType: string | null;
  resolved: boolean | null;
  dateFrom: string | null;
  dateTo: string | null;
}

export interface FilterStore {
  transactionFilters: TransactionFilters;
  setTransactionFilter: <K extends keyof TransactionFilters>(
    key: K,
    value: TransactionFilters[K]
  ) => void;
  resetTransactionFilters: () => void;

  fraudFilters: FraudFilters;
  setFraudFilter: <K extends keyof FraudFilters>(
    key: K,
    value: FraudFilters[K]
  ) => void;
  resetFraudFilters: () => void;
}

export interface NotificationStore {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (
    n: Omit<Notification, "id" | "createdAt" | "read">
  ) => void;
  markRead: (id: string) => void;
  markAllRead: () => void;
  removeNotification: (id: string) => void;
}
