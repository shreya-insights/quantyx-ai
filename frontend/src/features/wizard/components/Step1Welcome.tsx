import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "@/utils/cn";
import { Button } from "@/components/ui/Button";
import useWizardStore from "@/stores/wizard.store";

// ─── Schema defined outside component to avoid re-creation on render ─────────
const step1Schema = z.object({
  companyName: z.string().min(2, "Company name must be at least 2 characters"),
  industry: z.enum(["fintech", "ecommerce", "saas", "banking", "other"] as const, {
    error: "Please select your industry",
  }),
  companySize: z.enum(["1-10", "11-50", "51-200", "200+"] as const, {
    error: "Please select your company size",
  }),
});

type Step1Values = z.infer<typeof step1Schema>;

const INDUSTRIES = [
  { value: "fintech", label: "Fintech", emoji: "💳" },
  { value: "ecommerce", label: "E-commerce", emoji: "🛍️" },
  { value: "saas", label: "SaaS", emoji: "☁️" },
  { value: "banking", label: "Banking", emoji: "🏦" },
  { value: "other", label: "Other", emoji: "✨" },
] as const;

const SIZES = [
  { value: "1-10", label: "1–10", sub: "Solo or small team" },
  { value: "11-50", label: "11–50", sub: "Growing startup" },
  { value: "51-200", label: "51–200", sub: "Scale-up" },
  { value: "200+", label: "200+", sub: "Enterprise" },
] as const;

export function Step1Welcome() {
  const { data, updateData, goNext, isSubmitting } = useWizardStore();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<Step1Values>({
    mode: "onBlur",
    resolver: zodResolver(step1Schema),
    defaultValues: {
      companyName: data.companyName,
      industry: data.industry || undefined,
      companySize: data.companySize || undefined,
    },
  });

  const companyName = watch("companyName");
  const selectedIndustry = watch("industry");
  const selectedSize = watch("companySize");

  const onSubmit = (values: Step1Values) => {
    updateData(values);
    goNext();
  };

  return (
    <div className="max-w-lg mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Welcome to Quantyx
        </h1>
        <p className="mt-2 text-slate-500 dark:text-slate-400">
          Let's get your workspace set up. This takes about 3 minutes.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-6">
        {/* Company name */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label
              htmlFor="companyName"
              className="text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              Company name
            </label>
            <AnimatePresence>
              {companyName?.length > 0 && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="text-xs text-slate-400"
                >
                  {companyName.length} chars
                </motion.span>
              )}
            </AnimatePresence>
          </div>
          <input
            id="companyName"
            {...register("companyName")}
            placeholder="Acme Corp"
            autoFocus
            aria-invalid={!!errors.companyName}
            className={cn(
              "w-full rounded-lg border bg-white dark:bg-slate-800 dark:border-slate-600 text-slate-900 dark:text-slate-100 placeholder-slate-400 text-sm px-3 py-2.5 transition-colors",
              "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
              errors.companyName
                ? "border-red-400 focus:ring-red-500"
                : "border-slate-300"
            )}
          />
          <AnimatePresence>
            {errors.companyName && (
              <motion.p
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="text-red-500 text-xs overflow-hidden"
                role="alert"
              >
                {errors.companyName.message}
              </motion.p>
            )}
          </AnimatePresence>
        </div>

        {/* Industry */}
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Industry
          </span>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
            {INDUSTRIES.map(({ value, label, emoji }) => (
              <button
                key={value}
                type="button"
                onClick={() => setValue("industry", value, { shouldValidate: true })}
                aria-pressed={selectedIndustry === value}
                className={cn(
                  "flex flex-col items-center gap-1 rounded-xl border-2 p-3 transition-all duration-200 text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                  selectedIndustry === value
                    ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                    : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 text-slate-600 dark:text-slate-400"
                )}
              >
                <span className="text-xl" aria-hidden="true">{emoji}</span>
                {label}
              </button>
            ))}
          </div>
          <AnimatePresence>
            {errors.industry && (
              <motion.p
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="text-red-500 text-xs overflow-hidden"
                role="alert"
              >
                {errors.industry.message}
              </motion.p>
            )}
          </AnimatePresence>
        </div>

        {/* Company size */}
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Team size
          </span>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {SIZES.map(({ value, label, sub }) => (
              <button
                key={value}
                type="button"
                onClick={() => setValue("companySize", value, { shouldValidate: true })}
                aria-pressed={selectedSize === value}
                className={cn(
                  "flex flex-col items-start gap-0.5 rounded-xl border-2 p-3 transition-all duration-200 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                  selectedSize === value
                    ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                    : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600"
                )}
              >
                <span
                  className={cn(
                    "text-sm font-semibold",
                    selectedSize === value
                      ? "text-blue-700 dark:text-blue-300"
                      : "text-slate-700 dark:text-slate-300"
                  )}
                >
                  {label}
                </span>
                <span className="text-xs text-slate-500 dark:text-slate-400">{sub}</span>
              </button>
            ))}
          </div>
          <AnimatePresence>
            {errors.companySize && (
              <motion.p
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="text-red-500 text-xs overflow-hidden"
                role="alert"
              >
                {errors.companySize.message}
              </motion.p>
            )}
          </AnimatePresence>
        </div>

        {/* CTA */}
        <div className="flex justify-end pt-2">
          <Button
            type="submit"
            size="lg"
            loading={isSubmitting}
            aria-label="Continue to company setup"
          >
            Continue
          </Button>
        </div>
      </form>
    </div>
  );
}
