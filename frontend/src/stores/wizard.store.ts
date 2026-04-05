import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import type { WizardData, WizardStep, WizardStore } from "@/types/wizard.types";

const INITIAL_DATA: WizardData = {
  companyName: "",
  industry: "",
  companySize: "",
  companySlug: "",
  subscriptionTier: "starter",
  logoFile: null,
  logoPreview: null,
  fullName: "",
  jobTitle: "",
  avatarFile: null,
  avatarPreview: null,
  invites: [],
  completed: false,
};

const useWizardStore = create<WizardStore>()(
  persist(
    immer((set) => ({
      currentStep: 1 as WizardStep,
      direction: "forward" as const,
      data: INITIAL_DATA,
      isSubmitting: false,

      goNext: () =>
        set((s) => {
          if (s.currentStep < 5) {
            s.direction = "forward";
            s.currentStep = (s.currentStep + 1) as WizardStep;
          }
        }),

      goBack: () =>
        set((s) => {
          if (s.currentStep > 1) {
            s.direction = "backward";
            s.currentStep = (s.currentStep - 1) as WizardStep;
          }
        }),

      goToStep: (step) =>
        set((s) => {
          s.direction = step > s.currentStep ? "forward" : "backward";
          s.currentStep = step;
        }),

      updateData: (partial) =>
        set((s) => {
          Object.assign(s.data, partial);
        }),

      setSubmitting: (v) =>
        set((s) => {
          s.isSubmitting = v;
        }),

      reset: () =>
        set((s) => {
          s.currentStep = 1;
          s.direction = "forward";
          s.data = INITIAL_DATA;
          s.isSubmitting = false;
        }),
    })),
    {
      name: "quantyx-wizard",
      // File objects are not serializable — strip them from persisted state
      partialize: (s) => ({
        currentStep: s.currentStep,
        data: {
          ...s.data,
          logoFile: null,
          avatarFile: null,
        },
      }),
    }
  )
);

export default useWizardStore;
