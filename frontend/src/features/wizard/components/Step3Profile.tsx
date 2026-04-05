import { useCallback, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AnimatePresence, motion } from "framer-motion";
import { Camera, X } from "lucide-react";
import { cn } from "@/utils/cn";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import useWizardStore from "@/stores/wizard.store";

const step3Schema = z.object({
  fullName: z.string().min(2, "Full name must be at least 2 characters"),
  jobTitle: z.string().min(2, "Job title must be at least 2 characters"),
});

type Step3Values = z.infer<typeof step3Schema>;

export function Step3Profile() {
  const { data, updateData, goNext, goBack, isSubmitting } = useWizardStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Step3Values>({
    mode: "onBlur",
    resolver: zodResolver(step3Schema),
    defaultValues: {
      fullName: data.fullName,
      jobTitle: data.jobTitle,
    },
  });

  const handleFile = useCallback(
    (file: File | null) => {
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        updateData({ avatarFile: file, avatarPreview: e.target?.result as string });
      };
      reader.readAsDataURL(file);
    },
    [updateData]
  );

  const onSubmit = (values: Step3Values) => {
    updateData(values);
    goNext();
  };

  return (
    <div className="max-w-lg mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Your profile
        </h1>
        <p className="mt-2 text-slate-500 dark:text-slate-400">
          Tell us a bit about yourself — your team will see this.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-6">
        {/* Avatar upload */}
        <div className="flex flex-col items-center gap-3">
          <div className="relative">
            {data.avatarPreview ? (
              <img
                src={data.avatarPreview}
                alt="Profile avatar"
                className="w-24 h-24 rounded-full object-cover border-4 border-white dark:border-slate-800 shadow-md"
              />
            ) : (
              <div className="w-24 h-24 rounded-full bg-gradient-to-br from-blue-400 to-indigo-600 flex items-center justify-center shadow-md">
                <Camera className="w-8 h-8 text-white" aria-hidden="true" />
              </div>
            )}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              aria-label="Upload profile photo"
              className={cn(
                "absolute -bottom-1 -right-1 w-7 h-7 rounded-full flex items-center justify-center shadow-md transition-colors",
                "bg-blue-600 hover:bg-blue-700 text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              )}
            >
              <Camera className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          </div>

          {data.avatarPreview && (
            <button
              type="button"
              onClick={() => updateData({ avatarFile: null, avatarPreview: null })}
              className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 transition-colors"
              aria-label="Remove profile photo"
            >
              <X className="w-3 h-3" aria-hidden="true" /> Remove photo
            </button>
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

        {/* Full name */}
        <div>
          <Input
            label="Full name"
            placeholder="Jane Smith"
            autoFocus
            {...register("fullName")}
            error={errors.fullName?.message}
          />
          <AnimatePresence>
            {errors.fullName && (
              <motion.p
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="text-red-500 text-xs overflow-hidden mt-1"
                role="alert"
              >
                {errors.fullName.message}
              </motion.p>
            )}
          </AnimatePresence>
        </div>

        {/* Job title */}
        <div>
          <Input
            label="Job title"
            placeholder="Head of Finance"
            {...register("jobTitle")}
            error={errors.jobTitle?.message}
          />
          <AnimatePresence>
            {errors.jobTitle && (
              <motion.p
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="text-red-500 text-xs overflow-hidden mt-1"
                role="alert"
              >
                {errors.jobTitle.message}
              </motion.p>
            )}
          </AnimatePresence>
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
