import { useState } from "react";
import { Link } from "react-router-dom";
import { useLogin } from "../hooks/useAuth";
import { Button, Input } from "@/components/ui";
import { ROUTES } from "@/utils/constants";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const loginMutation = useLogin();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loginMutation.mutate({ email, password });
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link to={ROUTES.HOME} className="inline-flex items-center gap-2.5 mb-6">
            <img src="/monitor.png" alt="Quantyx AI logo" className="w-10 h-10" />
            <span className="text-2xl font-bold text-white">Quantyx AI</span>
          </Link>
          <h1 className="text-2xl font-bold text-white">Welcome back</h1>
          <p className="text-slate-400 mt-1 text-sm">Sign in to your analytics workspace</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8">
          {loginMutation.isError && (
            <div className="bg-red-900/30 border border-red-800 text-red-300 rounded-lg px-4 py-3 text-sm mb-5">
              {(loginMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Invalid email or password"}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <Input
              label="Email address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@company.com"
              className="bg-slate-800 border-slate-700 text-white placeholder-slate-500"
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              className="bg-slate-800 border-slate-700 text-white placeholder-slate-500"
            />
            <Button
              type="submit"
              className="w-full py-3"
              loading={loginMutation.isPending}
            >
              {loginMutation.isPending ? "Signing in…" : "Sign In"}
            </Button>
          </form>

          <p className="text-center text-slate-400 text-sm mt-6">
            Don't have an account?{" "}
            <Link to={ROUTES.REGISTER} className="text-blue-400 hover:text-blue-300">
              Create one free
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
