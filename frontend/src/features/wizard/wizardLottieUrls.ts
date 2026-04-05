/**
 * Vite-resolved URLs to Lottie JSON under src/assets/animations.
 * Using ?url avoids requesting /animations/*.json from public (those 404 → SPA HTML).
 */
import type { WizardStep } from "@/types/wizard.types";
import welcomeUrl from "@/assets/animations/welcome.json?url";
import setupUrl from "@/assets/animations/setup.json?url";
import profileUrl from "@/assets/animations/profile.json?url";
import teamUrl from "@/assets/animations/team.json?url";
import successUrl from "@/assets/animations/success.json?url";

export const WIZARD_STEP_LOTTIE_URL: Record<WizardStep, string> = {
  1: welcomeUrl,
  2: setupUrl,
  3: profileUrl,
  4: teamUrl,
  5: successUrl,
};

export const WIZARD_SUCCESS_LOTTIE_URL = successUrl;
