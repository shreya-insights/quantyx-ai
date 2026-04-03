import { api } from "@/lib/axios";
import type { TokenResponse, User } from "@/types/api.types";

export interface RegisterPayload {
  company_name: string;
  company_slug: string;
  admin_email: string;
  admin_password: string;
  admin_full_name: string;
}

export const authService = {
  register: (payload: RegisterPayload) =>
    api.post<TokenResponse>("/auth/register", payload).then((r) => r.data),

  login: (email: string, password: string) =>
    api.post<TokenResponse>("/auth/login", { email, password }).then((r) => r.data),

  refresh: (refreshToken: string) =>
    api.post<TokenResponse>("/auth/refresh", { refresh_token: refreshToken }).then((r) => r.data),

  me: () => api.get<User>("/auth/me").then((r) => r.data),

  inviteUser: (payload: { email: string; full_name: string; role: string; password: string }) =>
    api.post<User>("/auth/users/invite", payload).then((r) => r.data),
};
