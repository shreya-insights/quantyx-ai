import { motion } from "framer-motion";
import { CheckCircle2, Sparkles, Building2, User, Users, Check } from "lucide-react";
import { cn } from "@/utils/cn";
import type { WizardStep } from "@/types/wizard.types";

interface WizardProgressBarProps {
  currentStep: WizardStep;
  totalSteps: 5;
  completedSteps: WizardStep[];
  onStepClick: (step: WizardStep) => void;
}

const STEP_LABELS = ["Welcome", "Company", "Profile", "Invite", "Done"] as const;

const STEP_ICONS = [Sparkles, Building2, User, Users, Check] as const;

const TOTAL = 5;

export function WizardProgressBar({
  currentStep,
  completedSteps,
  onStepClick,
}: WizardProgressBarProps) {
  const progress = ((currentStep - 1) / (TOTAL - 1)) * 100;

  return (
    <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
      {/* Top row: thin animated fill bar + step counter */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex-1 relative h-1 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden mr-4">
          <motion.div
            className="absolute inset-y-0 left-0 bg-blue-600 rounded-full"
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: "easeInOut" }}
          />
        </div>
        <span className="text-xs font-medium text-slate-500 dark:text-slate-400 whitespace-nowrap">
          Step {currentStep} of {TOTAL}
        </span>
      </div>

      {/* Step indicators */}
      <div className="flex items-center justify-between">
        {(Array.from({ length: TOTAL }) as undefined[]).map((_, i) => {
          const step = (i + 1) as WizardStep;
          const isCompleted = completedSteps.includes(step);
          const isActive = step === currentStep;
          const isFuture = step > currentStep && !isCompleted;
          const Icon = STEP_ICONS[i];
          const isClickable = isCompleted && step !== currentStep;

          return (
            <div key={step} className="flex items-center flex-1">
              {/* Circle */}
              <div className="flex flex-col items-center">
                <button
                  type="button"
                  onClick={() => isClickable && onStepClick(step)}
                  disabled={!isClickable}
                  aria-label={`Go to step ${step}: ${STEP_LABELS[i]}`}
                  aria-current={isActive ? "step" : undefined}
                  className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2",
                    isCompleted &&
                      "bg-emerald-500 text-white cursor-pointer hover:bg-emerald-600",
                    isActive &&
                      "bg-blue-600 text-white ring-2 ring-blue-200 dark:ring-blue-800 cursor-default",
                    isFuture &&
                      "border-2 border-slate-300 dark:border-slate-600 text-slate-400 cursor-default"
                  )}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
                  ) : (
                    <Icon className="w-4 h-4" aria-hidden="true" />
                  )}
                </button>

                {/* Label — hidden on mobile */}
                <span
                  className={cn(
                    "hidden sm:block mt-1 text-xs font-medium transition-colors duration-300",
                    isActive
                      ? "text-blue-600 dark:text-blue-400"
                      : isCompleted
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-slate-400 dark:text-slate-500"
                  )}
                >
                  {STEP_LABELS[i]}
                </span>
              </div>

              {/* Connector line between steps */}
              {i < TOTAL - 1 && (
                <div className="flex-1 mx-2 relative h-0.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                  <motion.div
                    className="absolute inset-y-0 left-0 bg-blue-600 rounded-full"
                    animate={{
                      width: completedSteps.includes(step) ? "100%" : "0%",
                    }}
                    transition={{ duration: 0.4, ease: "easeInOut" }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
