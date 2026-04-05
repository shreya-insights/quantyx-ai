export type WizardStep = 1 | 2 | 3 | 4 | 5;

export interface InviteEntry {
  id: string;
  email: string;
  role: "analyst" | "viewer";
  status: "pending" | "sent" | "error";
}

export interface WizardData {
  // Step 1 — Welcome
  companyName: string;
  industry: "fintech" | "ecommerce" | "saas" | "banking" | "other" | "";
  companySize: "1-10" | "11-50" | "51-200" | "200+" | "";
  // Step 2 — Company Setup
  companySlug: string;
  subscriptionTier: "starter" | "growth" | "enterprise";
  logoFile: File | null;
  logoPreview: string | null;
  // Step 3 — Admin Profile
  fullName: string;
  jobTitle: string;
  avatarFile: File | null;
  avatarPreview: string | null;
  // Step 4 — Invite Team
  invites: InviteEntry[];
  // Step 5 — Completion
  completed: boolean;
}

export interface WizardStore {
  currentStep: WizardStep;
  direction: "forward" | "backward";
  data: WizardData;
  isSubmitting: boolean;
  goNext: () => void;
  goBack: () => void;
  goToStep: (step: WizardStep) => void;
  updateData: (partial: Partial<WizardData>) => void;
  setSubmitting: (v: boolean) => void;
  reset: () => void;
}
