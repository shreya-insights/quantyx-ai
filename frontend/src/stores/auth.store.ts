import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, TokenResponse } from "@/types/api.types";

interface PendingInvite {
  email: string;
  role: string;
  companyName: string;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  /** Raw invite token received from email link — cleared after wizard completes. */
  inviteToken: string | null;
  /** Decoded invite metadata shown during the onboarding wizard. */
  pendingInvite: PendingInvite | null;
  login: (tokens: TokenResponse, user: User) => void;
  /** Update tokens after /auth/refresh without replacing user (WebSocket, etc.). */
  setTokens: (tokens: TokenResponse) => void;
  logout: () => void;
  setUser: (user: User) => void;
  setInviteToken: (token: string | null) => void;
  setPendingInvite: (invite: PendingInvite | null) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      inviteToken: null,
      pendingInvite: null,

      login: (tokens, user) => {
        localStorage.setItem("access_token", tokens.access_token);
        localStorage.setItem("refresh_token", tokens.refresh_token);
        set({
          user,
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          isAuthenticated: true,
        });
      },

      setTokens: (tokens) => {
        localStorage.setItem("access_token", tokens.access_token);
        localStorage.setItem("refresh_token", tokens.refresh_token);
        set({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
        });
      },

      logout: () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          inviteToken: null,
          pendingInvite: null,
        });
      },

      setUser: (user) => set({ user }),
      setInviteToken: (token) => set({ inviteToken: token }),
      setPendingInvite: (invite) => set({ pendingInvite: invite }),
    }),
    {
      name: "quantyx-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        user: state.user,
        // inviteToken/pendingInvite are session-only — never persisted
      }),
    }
  )
);
