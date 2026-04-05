import type { ReactNode } from "react";
import { CheckCircle2, Building2, User, Users, Sparkles } from "lucide-react";
import { WizardProgressBar } from "./WizardProgressBar";
import { LottiePlayer } from "./components/LottiePlayer";
import { StepAnimator } from "./components/StepAnimator";
import useWizardStore from "@/stores/wizard.store";
import type { WizardStep } from "@/types/wizard.types";

interface WizardShellProps {
  children: ReactNode;
}

const STEP_LOTTIE_MAP: Record<WizardStep, string> = {
  1: "/animations/welcome.json",
  2: "/animations/setup.json",
  3: "/animations/profile.json",
  4: "/animations/team.json",
  5: "/animations/success.json",
};

const STEP_TITLES: Record<WizardStep, string> = {
  1: "Welcome aboard",
  2: "Set up your workspace",
  3: "Complete your profile",
  4: "Build your team",
  5: "You're ready to go",
};

const STEP_SUBTITLES: Record<WizardStep, string> = {
  1: "Tell us about your company so we can tailor Quantyx for you.",
  2: "Choose a plan and customise your workspace identity.",
  3: "Add your name and photo — your team will see this.",
  4: "Invite colleagues to collaborate from day one.",
  5: "Your Quantyx workspace is fully configured.",
};

/**
 * Lucide icons used as branded placeholders while Lottie JSON files load.
 * These make the left panel feel intentional even before animations are present.
 */
const STEP_FALLBACK_ICONS: Record<WizardStep, ReactNode> = {
  1: <Sparkles className="w-8 h-8 text-white/80" aria-hidden="true" />,
  2: <Building2 className="w-8 h-8 text-white/80" aria-hidden="true" />,
  3: <User       className="w-8 h-8 text-white/80" aria-hidden="true" />,
  4: <Users      className="w-8 h-8 text-white/80" aria-hidden="true" />,
  5: <CheckCircle2 className="w-8 h-8 text-white/80" aria-hidden="true" />,
};

/**
 * Computes which steps are considered "completed" for the progress bar.
 * A step is completed if the user has moved past it.
 */
function getCompletedSteps(currentStep: WizardStep): WizardStep[] {
  const completed: WizardStep[] = [];
  for (let s = 1; s < currentStep; s++) {
    completed.push(s as WizardStep);
  }
  return completed;
}

export function WizardShell({ children }: WizardShellProps) {
  const { currentStep, direction, goToStep } = useWizardStore();
  const completedSteps = getCompletedSteps(currentStep);

  return (
    <div className="min-h-screen flex bg-white dark:bg-slate-900">
      {/* ── Left decorative panel — hidden on mobile ─────────────────────── */}
      <aside
        className="hidden lg:flex w-2/5 bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 flex-col items-center justify-center p-12 relative overflow-hidden"
        aria-hidden="true"
      >
        {/* Subtle background circles for depth */}
        <div className="absolute -top-24 -left-24 w-64 h-64 rounded-full bg-white/5 pointer-events-none" />
        <div className="absolute -bottom-16 -right-16 w-48 h-48 rounded-full bg-white/5 pointer-events-none" />

        {/* Logo */}
        <img
          src="/favicon.svg"
          alt="Quantyx"
          className="mb-8 h-10 w-auto brightness-200"
        />

        {/* Step illustration — shows icon fallback until Lottie JSON files are placed */}
        <LottiePlayer
          src={STEP_LOTTIE_MAP[currentStep]}
          loop
          className="w-64 h-64"
          fallbackIcon={STEP_FALLBACK_ICONS[currentStep]}
        />

        {/* Step title & subtitle */}
        <h2 className="text-white text-2xl font-bold mt-6 text-center leading-tight">
          {STEP_TITLES[currentStep]}
        </h2>
        <p className="text-blue-200 mt-2 text-center text-sm max-w-xs leading-relaxed">
          {STEP_SUBTITLES[currentStep]}
        </p>
      </aside>

      {/* ── Right form panel ──────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-h-screen">
        <WizardProgressBar
          currentStep={currentStep}
          totalSteps={5}
          completedSteps={completedSteps}
          onStepClick={goToStep}
        />

        <main className="flex-1 overflow-y-auto p-6 lg:p-12">
          <StepAnimator stepKey={currentStep} direction={direction}>
            {children}
          </StepAnimator>
        </main>
      </div>
    </div>
  );
}
