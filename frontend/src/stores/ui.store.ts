import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import type { UIStore } from "@/types/store.types";

const useUIStore = create<UIStore>()(
  persist(
    immer((set) => ({
      sidebarCollapsed: false,
      toggleSidebar: () =>
        set((state) => {
          state.sidebarCollapsed = !state.sidebarCollapsed;
        }),
      setSidebarCollapsed: (v) =>
        set((state) => {
          state.sidebarCollapsed = v;
        }),

      activeModal: null,
      openModal: (id) =>
        set((state) => {
          state.activeModal = id;
        }),
      closeModal: () =>
        set((state) => {
          state.activeModal = null;
        }),

      pageLoading: false,
      setPageLoading: (v) =>
        set((state) => {
          state.pageLoading = v;
        }),

      pageSize: 20,
      setPageSize: (n) =>
        set((state) => {
          state.pageSize = n;
        }),
    })),
    {
      name: "quantyx-ui",
      // Never persist activeModal (ghost modal on refresh) or pageLoading
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        pageSize: state.pageSize,
      }),
    }
  )
);

export default useUIStore;
