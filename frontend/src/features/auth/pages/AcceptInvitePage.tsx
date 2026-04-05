import { useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { Eye, EyeOff, UserPlus, AlertCircle, CheckCircle2 } from "lucide-react";
import { cn } from "@/utils/cn";
import { Button } from "@/components/ui/Button";
import { invitationService, type AcceptInvitePayload } from "@/services/invitation.service";
import { useAuthStore } from "@/stores/auth.store";
import { authService } from "@/services/auth.service";
import { ROUTES } from "@/utils/constants";
import { LottiePlayer } from "@/features/wizard/components/LottiePlayer";
import { WIZARD_SUCCESS_LOTTIE_URL } from "@/features/wizard/wizardLottieUrls";

// ─── Form state ───────────────────────────────────────────────────────────────

interface FormValues {
  full_name: string;
  password: string;
  confirm_password: string;
}

interface FormErrors {
  full_name?: string;
  password?: string;
  confirm_password?: string;
}

function validateForm(values: FormValues): FormErrors {
  const errors: FormErrors = {};
  if (!values.full_name.trim() || values.full_name.trim().length < 2) {
    errors.full_name = "Full name must be at least 2 characters";
  }
  if (values.password.length < 8) {
    errors.password = "Password must be at least 8 characters";
  } else if (!/[A-Z]/.test(values.password)) {
    errors.password = "Password must contain at least one uppercase letter";
  } else if (!/[0-9]/.test(values.password)) {
    errors.password = "Password must contain at least one digit";
  }
  if (values.password !== values.confirm_password) {
    errors.confirm_password = "Passwords do not match";
  }
  return errors;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function FieldError({ message }: { message: string }) {
  return (
    <motion.p
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: "auto", opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="text-red-500 dark:text-red-400 text-xs mt-1 overflow-hidden"
      role="alert"
    >
      {message}
    </motion.p>
  );
}

function InvalidTokenState({ message }: { message: string }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 px-4">
      <div className="w-full max-w-md text-center">
        <div className="w-16 h-16 rounded-2xl bg-red-100 dark:bg-red-900/20 flex items-center justify-center mx-auto mb-6">
          <AlertCircle className="w-8 h-8 text-red-500" aria-hidden="true" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-3">
          Invitation not valid
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mb-8 leading-relaxed">
          {message}
        </p>
        <Link
          to={ROUTES.LOGIN}
          className="inline-flex items-center gap-2 text-blue-600 dark:text-blue-400 font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        >
          Back to sign in
        </Link>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AcceptInvitePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const prefersReducedMotion = useReducedMotion();

  const token = searchParams.get("token") ?? "";

  const [values, setValues] = useState<FormValues>({
    full_name: "",
    password: "",
    confirm_password: "",
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [accepted, setAccepted] = useState(false);

  // ── Validate token on mount ────────────────────────────────────────────────
  const { data: tokenInfo, isLoading: validating, isError: fetchError } = useQuery({
    queryKey: ["invitation-validate", token],
    queryFn: () => invitationService.validate(token),
    enabled: !!token,
    retry: 0,
    staleTime: 60_000,
  });

  // ── Accept invitation mutation ─────────────────────────────────────────────
  const acceptMutation = useMutation({
    mutationFn: (payload: AcceptInvitePayload) => invitationService.accept(payload),
    retry: 0,
    onSuccess: async (tokens) => {
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
      const user = await authService.me();
      login(tokens, user);
      setAccepted(true);
      // Navigate to dashboard after Lottie animation completes (2s)
      setTimeout(() => navigate(ROUTES.DASHBOARD, { replace: true }), 2000);
    },
  });

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleChange = (field: keyof FormValues) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setValues((prev) => ({ ...prev, [field]: e.target.value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const validationErrors = validateForm(values);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }
    acceptMutation.mutate({
      token,
      full_name: values.full_name.trim(),
      password: values.password,
    });
  };

  // ── Guard: no token in URL ─────────────────────────────────────────────────
  if (!token) {
    return (
      <InvalidTokenState message="No invitation token found. Please check the link in your email and try again." />
    );
  }

  // ── Loading state ──────────────────────────────────────────────────────────
  if (validating) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-4 border-blue-600/30 border-t-blue-600 animate-spin" aria-label="Validating invitation" />
          <p className="text-slate-500 dark:text-slate-400 text-sm">Checking your invitation…</p>
        </div>
      </div>
    );
  }

  // ── Invalid / expired token ────────────────────────────────────────────────
  if (fetchError || !tokenInfo?.valid) {
    return (
      <InvalidTokenState
        message="This invitation link has expired or already been used. Please ask your admin to send a new invite."
      />
    );
  }

  // ── Success animation (after accept) ──────────────────────────────────────
  if (accepted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
        <motion.div
          initial={{ opacity: 0, scale: prefersReducedMotion ? 1 : 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.35 }}
          className="flex flex-col items-center gap-4 text-center"
        >
          <LottiePlayer
            src={WIZARD_SUCCESS_LOTTIE_URL}
            loop={false}
            autoplay
            className="w-40 h-40"
          />
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">
            Welcome to {tokenInfo.company_name}!
          </h2>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            Redirecting you to the dashboard…
          </p>
        </motion.div>
      </div>
    );
  }

  // ── Registration form ──────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 px-4 py-12">
      <motion.div
        initial={{ opacity: 0, y: prefersReducedMotion ? 0 : 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="w-full max-w-md"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-blue-600 flex items-center justify-center mx-auto mb-5">
            <UserPlus className="w-7 h-7 text-white" aria-hidden="true" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Join {tokenInfo.company_name}
          </h1>
          <p className="mt-2 text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
            You've been invited as a{" "}
            <span className="font-semibold text-slate-700 dark:text-slate-300 capitalize">
              {tokenInfo.role}
            </span>
            . Set up your account to get started.
          </p>
        </div>

        {/* Card */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-8">
          <form onSubmit={handleSubmit} noValidate>
            <div className="space-y-5">

              {/* Email — read-only, pre-filled from token */}
              <div>
                <label
                  htmlFor="email"
                  className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                >
                  Email address
                </label>
                <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" aria-hidden="true" />
                  <span
                    id="email"
                    className="text-sm text-slate-700 dark:text-slate-300"
                    aria-label="Email address (pre-filled from invitation)"
                  >
                    {tokenInfo.email}
                  </span>
                </div>
              </div>

              {/* Full name */}
              <div>
                <label
                  htmlFor="full_name"
                  className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                >
                  Full name <span aria-hidden="true" className="text-red-500">*</span>
                </label>
                <input
                  id="full_name"
                  type="text"
                  autoComplete="name"
                  value={values.full_name}
                  onChange={handleChange("full_name")}
                  aria-invalid={!!errors.full_name}
                  aria-describedby={errors.full_name ? "full_name_error" : undefined}
                  placeholder="Jane Smith"
                  className={cn(
                    "w-full px-3.5 py-2.5 rounded-xl border text-sm text-slate-900 dark:text-white placeholder-slate-400 bg-white dark:bg-slate-800",
                    "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors",
                    errors.full_name
                      ? "border-red-400 dark:border-red-600"
                      : "border-slate-200 dark:border-slate-700"
                  )}
                />
                <AnimatePresence>
                  {errors.full_name && (
                    <FieldError message={errors.full_name} />
                  )}
                </AnimatePresence>
              </div>

              {/* Password */}
              <div>
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                >
                  Password <span aria-hidden="true" className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    value={values.password}
                    onChange={handleChange("password")}
                    aria-invalid={!!errors.password}
                    aria-describedby={errors.password ? "password_error" : "password_hint"}
                    placeholder="Min 8 chars, 1 uppercase, 1 digit"
                    className={cn(
                      "w-full px-3.5 py-2.5 pr-11 rounded-xl border text-sm text-slate-900 dark:text-white placeholder-slate-400 bg-white dark:bg-slate-800",
                      "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors",
                      errors.password
                        ? "border-red-400 dark:border-red-600"
                        : "border-slate-200 dark:border-slate-700"
                    )}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((s) => !s)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" aria-hidden="true" />
                    ) : (
                      <Eye className="w-4 h-4" aria-hidden="true" />
                    )}
                  </button>
                </div>
                <AnimatePresence>
                  {errors.password && <FieldError message={errors.password} />}
                </AnimatePresence>
              </div>

              {/* Confirm password */}
              <div>
                <label
                  htmlFor="confirm_password"
                  className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                >
                  Confirm password <span aria-hidden="true" className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    id="confirm_password"
                    type={showConfirm ? "text" : "password"}
                    autoComplete="new-password"
                    value={values.confirm_password}
                    onChange={handleChange("confirm_password")}
                    aria-invalid={!!errors.confirm_password}
                    aria-describedby={errors.confirm_password ? "confirm_error" : undefined}
                    placeholder="Re-enter your password"
                    className={cn(
                      "w-full px-3.5 py-2.5 pr-11 rounded-xl border text-sm text-slate-900 dark:text-white placeholder-slate-400 bg-white dark:bg-slate-800",
                      "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors",
                      errors.confirm_password
                        ? "border-red-400 dark:border-red-600"
                        : "border-slate-200 dark:border-slate-700"
                    )}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirm((s) => !s)}
                    aria-label={showConfirm ? "Hide confirmation password" : "Show confirmation password"}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
                  >
                    {showConfirm ? (
                      <EyeOff className="w-4 h-4" aria-hidden="true" />
                    ) : (
                      <Eye className="w-4 h-4" aria-hidden="true" />
                    )}
                  </button>
                </div>
                <AnimatePresence>
                  {errors.confirm_password && (
                    <FieldError message={errors.confirm_password} />
                  )}
                </AnimatePresence>
              </div>

              {/* API error */}
              <AnimatePresence>
                {acceptMutation.isError && (
                  <motion.div
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="flex items-start gap-2.5 p-3.5 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
                    role="alert"
                  >
                    <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" aria-hidden="true" />
                    <p className="text-sm text-red-700 dark:text-red-300">
                      {(acceptMutation.error as { response?: { data?: { detail?: string } } })
                        ?.response?.data?.detail ?? "Something went wrong. Please try again."}
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>

              <Button
                type="submit"
                size="lg"
                className="w-full"
                loading={acceptMutation.isPending}
                aria-label="Create account and accept invitation"
              >
                Create account
              </Button>
            </div>
          </form>
        </div>

        <p className="text-center text-xs text-slate-400 dark:text-slate-600 mt-6">
          Already have an account?{" "}
          <Link
            to={ROUTES.LOGIN}
            className="text-blue-600 dark:text-blue-400 hover:underline"
          >
            Sign in
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
