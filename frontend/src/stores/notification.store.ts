import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { Notification, NotificationStore } from "@/types/store.types";

const MAX_NOTIFICATIONS = 100;

const useNotificationStore = create<NotificationStore>()(
  immer((set, get) => ({
    notifications: [],

    get unreadCount() {
      return get().notifications.filter((n) => !n.read).length;
    },

    addNotification: (n) =>
      set((state) => {
        const notification: Notification = {
          ...n,
          id: crypto.randomUUID(),
          createdAt: new Date().toISOString(),
          read: false,
        };
        state.notifications.unshift(notification);
        if (state.notifications.length > MAX_NOTIFICATIONS) {
          state.notifications = state.notifications.slice(0, MAX_NOTIFICATIONS);
        }
      }),

    markRead: (id) =>
      set((state) => {
        const notification = state.notifications.find((n) => n.id === id);
        if (notification) notification.read = true;
      }),

    markAllRead: () =>
      set((state) => {
        state.notifications.forEach((n) => {
          n.read = true;
        });
      }),

    removeNotification: (id) =>
      set((state) => {
        state.notifications = state.notifications.filter((n) => n.id !== id);
      }),
  }))
);

export default useNotificationStore;
