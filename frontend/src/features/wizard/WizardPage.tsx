import { Navigate } from "react-router-dom";
import { WizardShell } from "./WizardShell";
import { Step1Welcome } from "./components/Step1Welcome";
import { Step2Company } from "./components/Step2Company";
import { Step3Profile } from "./components/Step3Profile";
import { Step4InviteTeam } from "./components/Step4InviteTeam";
import { Step5Success } from "./components/Step5Success";
import useWizardStore from "@/stores/wizard.store";
import { ROUTES } from "@/utils/constants";
import type { WizardStep } from "@/types/wizard.types";

const STEP_COMPONENTS: Record<WizardStep, React.ReactElement> = {
  1: <Step1Welcome />,
  2: <Step2Company />,
  3: <Step3Profile />,
  4: <Step4InviteTeam />,
  5: <Step5Success />,
};

export default function WizardPage() {
  const { currentStep, data } = useWizardStore();

  // Already completed — send straight to dashboard
  if (data.completed) {
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  return <WizardShell>{STEP_COMPONENTS[currentStep]}</WizardShell>;
}
