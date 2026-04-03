import { useState } from "react";
import { Link } from "react-router-dom";
import { useRegister } from "../hooks/useAuth";
import { Button, Input } from "@/components/ui";
import { ROUTES } from "@/utils/constants";

interface FormState {
  company_name: string;
  company_slug: string;
  admin_email: string;
  admin_password: string;
  admin_full_name: string;
}

function toSlug(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export default function RegisterPage() {
  const [form, setForm] = useState<FormState>({
    company_name: "",
    company_slug: "",
    admin_email: "",
    admin_password: "",
    admin_full_name: "",
  });

  const registerMutation = useRegister();

  const update = (field: keyof FormState, value: string) => {
    setForm((prev) => {
      const next = { ...prev, [field]: value };
      if (field === "company_name") next.company_slug = toSlug(value);
      return next;
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    registerMutation.mutate(form);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <Link to={ROUTES.HOME} className="inline-flex items-center gap-2.5 mb-6">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-lg font-bold text-white">Q</div>
            <span className="text-2xl font-bold text-white">Quantyx AI</span>
          </Link>
          <h1 className="text-2xl font-bold text-white">Create your workspace</h1>
          <p className="text-slate-400 mt-1 text-sm">14-day free trial · No credit card required</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8">
          {registerMutation.isError && (
            <div className="bg-red-900/30 border border-red-800 text-red-300 rounded-lg px-4 py-3 text-sm mb-5">
              {(registerMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Registration failed"}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <Input
              label="Company Name"
              value={form.company_name}
              onChange={(e) => update("company_name", e.target.value)}
              required
              placeholder="Acme Corp"
              className="bg-slate-800 border-slate-700 text-white placeholder-slate-500"
            />

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">
                Company Slug{" "}
                <span className="font-normal text-slate-500">(URL identifier)</span>
              </label>
              <div className="flex items-center bg-slate-800 border border-slate-700 rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-blue-500">
                <span className="pl-4 pr-2 text-slate-500 text-sm flex-shrink-0">quantyx.ai/</span>
                <input
                  type="text"
                  value={form.company_slug}
                  onChange={(e) => update("company_slug", e.target.value)}
                  required
                  pattern="^[a-z0-9-]+$"
                  className="flex-1 bg-transparent text-white pr-4 py-2.5 text-sm focus:outline-none"
                />
              </div>
            </div>

            <Input
              label="Your Full Name"
              value={form.admin_full_name}
              onChange={(e) => update("admin_full_name", e.target.value)}
              required
              placeholder="Jane Doe"
              className="bg-slate-800 border-slate-700 text-white placeholder-slate-500"
            />

            <Input
              label="Work Email"
              type="email"
              value={form.admin_email}
              onChange={(e) => update("admin_email", e.target.value)}
              required
              placeholder="jane@acmecorp.com"
              className="bg-slate-800 border-slate-700 text-white placeholder-slate-500"
            />

            <Input
              label="Password"
              type="password"
              value={form.admin_password}
              onChange={(e) => update("admin_password", e.target.value)}
              required
              minLength={8}
              placeholder="Min 8 chars, 1 uppercase, 1 number"
              className="bg-slate-800 border-slate-700 text-white placeholder-slate-500"
            />

            <Button type="submit" className="w-full py-3" loading={registerMutation.isPending}>
              {registerMutation.isPending ? "Creating workspace…" : "Create Free Workspace →"}
            </Button>
          </form>

          <p className="text-center text-slate-400 text-sm mt-6">
            Already have an account?{" "}
            <Link to={ROUTES.LOGIN} className="text-blue-400 hover:text-blue-300">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
