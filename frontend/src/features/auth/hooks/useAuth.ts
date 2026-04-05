import { useMutation } from "@tanstack/react-query";
import { useNavigate, useLocation } from "react-router-dom";
import { authService, type RegisterPayload } from "@/services/auth.service";
import { useAuthStore } from "@/stores/auth.store";
import { ROUTES } from "@/utils/constants";

export function useLogin() {
  const { login } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: Location })?.from?.pathname ?? ROUTES.DASHBOARD;

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authService.login(email, password),
    onSuccess: async (tokens) => {
      localStorage.setItem("access_token", tokens.access_token);
      const user = await authService.me();
      login(tokens, user);
      navigate(from, { replace: true });
    },
  });
}

export function useRegister() {
  const { login } = useAuthStore();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: (payload: RegisterPayload) => authService.register(payload),
    onSuccess: async (tokens) => {
      localStorage.setItem("access_token", tokens.access_token);
      const user = await authService.me();
      login(tokens, user);
      navigate(ROUTES.ONBOARDING);
    },
  });
}
