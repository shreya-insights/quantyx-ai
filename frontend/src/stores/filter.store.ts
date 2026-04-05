import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { FilterStore, FraudFilters, TransactionFilters } from "@/types/store.types";

const INITIAL_TRANSACTION_FILTERS: TransactionFilters = {
  search: "",
  status: null,
  type: null,
  dateFrom: null,
  dateTo: null,
  accountId: null,
  merchantId: null,
};

const INITIAL_FRAUD_FILTERS: FraudFilters = {
  severity: null,
  alertType: null,
  resolved: null,
  dateFrom: null,
  dateTo: null,
};

// Not persisted — filters reset on refresh intentionally.
// Filter objects feed directly into TanStack Query cache keys:
// useQuery({ queryKey: ['transactions', transactionFilters], ... })
const useFilterStore = create<FilterStore>()(
  immer((set) => ({
    transactionFilters: { ...INITIAL_TRANSACTION_FILTERS },
    setTransactionFilter: (key, value) =>
      set((state) => {
        (state.transactionFilters[key] as TransactionFilters[typeof key]) = value;
      }),
    resetTransactionFilters: () =>
      set((state) => {
        state.transactionFilters = { ...INITIAL_TRANSACTION_FILTERS };
      }),

    fraudFilters: { ...INITIAL_FRAUD_FILTERS },
    setFraudFilter: (key, value) =>
      set((state) => {
        (state.fraudFilters[key] as FraudFilters[typeof key]) = value;
      }),
    resetFraudFilters: () =>
      set((state) => {
        state.fraudFilters = { ...INITIAL_FRAUD_FILTERS };
      }),
  }))
);

export default useFilterStore;
