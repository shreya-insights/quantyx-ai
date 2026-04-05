import { useCallback, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AnimatePresence, motion } from "framer-motion";
import { Upload, X, Check } from "lucide-react";
import { cn } from "@/utils/cn";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import useWizardStore from "@/stores/wizard.store";

const step2Schema = z.object({
  companySlug: z
    .string()
    .min(3, "Slug must be at least 3 characters")
    .regex(/^[a-z0-9-]+$/, "Only lowercase letters, numbers and hyphens"),
  subscriptionTier: z.enum(["starter", "growth", "enterprise"]),
});

type Step2Values = z.infer<typeof step2Schema>;

const TIERS = [
  {
    value: "starter" as const,
    label: "Starter",
    price: "Free",
    features: ["Up to 10k transactions", "1 workspace", "Email support"],
  },
  {
    value: "growth" as const,
    label: "Growth",
    price: "$49/mo",
    features: ["Up to 500k transactions", "5 workspaces", "Priority support"],
    popular: true,
  },
  {
    value: "enterprise" as const,
    label: "Enterprise",
    price: "Custom",
    features: ["Unlimited transactions", "Unlimited workspaces", "Dedicated CSM"],
  },
] as const;

function toSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function Step2Company() {
  const { data, updateData, goNext, goBack, isSubmitting } = useWizardStore();
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<Step2Values>({
    mode: "onBlur",
    resolver: zodResolver(step2Schema),
    defaultValues: {
      companySlug:
        data.companySlug || toSlug(data.companyName),
      subscriptionTier: data.subscriptionTier,
    },
  });

  const selectedTier = watch("subscriptionTier");

  const handleFile = useCallback(
    (file: File | null) => {
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        updateData({ logoFile: file, logoPreview: e.target?.result as string });
      };
      reader.readAsDataURL(file);
    },
    [updateData]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file?.type.startsWith("image/")) handleFile(file);
    },
    [handleFile]
  );

  const onSubmit = (values: Step2Values) => {
    updateData(values);
    goNext();
  };

  return (
    <div className="max-w-lg mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Company setup
        </h1>
        <p className="mt-2 text-slate-500 dark:text-slate-400">
          Configure your workspace and choose a plan.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-6">
        {/* Slug */}
        <div>
          <Input
            label="Workspace URL"
            leftAddon="quantyx.app/"
            placeholder="acme-corp"
            {...register("companySlug")}
            error={errors.companySlug?.message}
            aria-describedby={errors.companySlug ? "slug-error" : undefined}
          />
          <p className="mt-1 text-xs text-slate-400">
            Lowercase letters, numbers and hyphens only
          </p>
        </div>

        {/* Tier cards */}
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Choose a plan
          </span>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {TIERS.map((tier) => {
            const { value, label, price, features } = tier;
            return (
              <button
                key={value}
                type="button"
                onClick={() => setValue("subscriptionTier", value, { shouldValidate: true })}
                aria-pressed={selectedTier === value}
                className={cn(
                  "relative flex flex-col items-start gap-2 rounded-xl border-2 p-4 text-left transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                  selectedTier === value
                    ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                    : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600"
                )}
              >
                {"popular" in tier && tier.popular && (
                  <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-medium px-2 py-0.5 rounded-full">
                    Popular
                  </span>
                )}
                <div className="flex items-center justify-between w-full">
                  <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                    {label}
                  </span>
                  {selectedTier === value && (
                    <Check className="w-4 h-4 text-blue-600" aria-hidden="true" />
                  )}
                </div>
                <span className="text-xl font-bold text-slate-900 dark:text-white">
                  {price}
                </span>
                <ul className="space-y-1">
                  {features.map((f) => (
                    <li key={f} className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                      <span className="text-emerald-500" aria-hidden="true">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
              </button>
            );
          })}
          </div>
          <AnimatePresence>
            {errors.subscriptionTier && (
              <motion.p
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="text-red-500 text-xs overflow-hidden"
                role="alert"
              >
                {errors.subscriptionTier.message}
              </motion.p>
            )}
          </AnimatePresence>
        </div>

        {/* Logo upload */}
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Company logo{" "}
            <span className="text-slate-400 font-normal">(optional)</span>
          </span>

          {data.logoPreview ? (
            <div className="flex items-center gap-3">
              <img
                src={data.logoPreview}
                alt="Company logo preview"
                className="w-16 h-16 rounded-xl object-cover border border-slate-200 dark:border-slate-700"
              />
              <button
                type="button"
                onClick={() => updateData({ logoFile: null, logoPreview: null })}
                className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 transition-colors"
                aria-label="Remove logo"
              >
                <X className="w-3 h-3" aria-hidden="true" /> Remove
              </button>
            </div>
          ) : (
            <motion.div
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
              animate={{ borderColor: isDragging ? "#3b82f6" : "#e2e8f0" }}
              transition={{ duration: 0.2 }}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
              aria-label="Upload company logo"
              className={cn(
                "flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-8 cursor-pointer transition-colors",
                isDragging
                  ? "bg-blue-50 dark:bg-blue-900/20"
                  : "hover:bg-slate-50 dark:hover:bg-slate-800/50"
              )}
            >
              <Upload className="w-6 h-6 text-slate-400" aria-hidden="true" />
              <p className="text-sm text-slate-500 dark:text-slate-400 text-center">
                <span className="font-medium text-blue-600">Browse</span> or drag & drop
              </p>
              <p className="text-xs text-slate-400">PNG, JPG, SVG up to 2MB</p>
            </motion.div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="sr-only"
            aria-hidden="true"
            onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          />
        </div>

        {/* CTA */}
        <div className="flex justify-between pt-2">
          <Button type="button" variant="outline" size="lg" onClick={goBack}>
            Back
          </Button>
          <Button type="submit" size="lg" loading={isSubmitting}>
            Continue
          </Button>
        </div>
      </form>
    </div>
  );
}
