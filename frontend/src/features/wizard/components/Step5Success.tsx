import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Building2, CreditCard, Users, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { LottiePlayer } from "./LottiePlayer";
import { WIZARD_SUCCESS_LOTTIE_URL } from "../wizardLottieUrls";
import useWizardStore from "@/stores/wizard.store";
import { ROUTES } from "@/utils/constants";

const TIER_LABELS = {
  starter: "Starter (Free)",
  growth: "Growth ($49/mo)",
  enterprise: "Enterprise (Custom)",
} as const;

// Stagger animation variants for summary cards
const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } },
};

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: { duration: 0.35, ease: [0.25, 0.1, 0.25, 1.0] as [number, number, number, number] },
  },
};

interface SummaryCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
}

function SummaryCard({ icon, label, value }: SummaryCardProps) {
  return (
    <motion.div
      variants={itemVariants}
      className="flex items-center gap-3 p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50"
    >
      <div className="w-10 h-10 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-blue-600 dark:text-blue-400 flex-shrink-0">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
        <p className="text-sm font-semibold text-slate-900 dark:text-white truncate">{value}</p>
      </div>
    </motion.div>
  );
}

export function Step5Success() {
  const navigate = useNavigate();
  const { data, updateData, reset } = useWizardStore();
  const [lottieComplete, setLottieComplete] = useState(false);

  const sentInvites = data.invites.filter((i) => i.status === "sent").length;

  const handleGoToDashboard = () => {
    updateData({ completed: true });
    // Brief delay so the persist middleware writes before navigation
    setTimeout(() => {
      reset();
      navigate(ROUTES.DASHBOARD, { replace: true });
    }, 50);
  };

  return (
    <div className="max-w-lg mx-auto flex flex-col items-center text-center">
      {/* Lottie success — loop=false, stagger reveals summary after it completes */}
      <LottiePlayer
        src={WIZARD_SUCCESS_LOTTIE_URL}
        loop={false}
        autoplay
        className="w-48 h-48"
        onComplete={() => setLottieComplete(true)}
      />

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
        className="mt-2"
      >
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          You're all set!
        </h1>
        <p className="mt-2 text-slate-500 dark:text-slate-400">
          Your Quantyx workspace is ready. Here's a summary of what we set up.
        </p>
      </motion.div>

      {/* Summary cards — animate in after Lottie finishes */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate={lottieComplete ? "visible" : "hidden"}
        className="w-full mt-6 grid grid-cols-1 gap-3 text-left"
      >
        <SummaryCard
          icon={<Building2 className="w-5 h-5" aria-hidden="true" />}
          label="Company"
          value={data.companyName || "—"}
        />
        <SummaryCard
          icon={<CreditCard className="w-5 h-5" aria-hidden="true" />}
          label="Plan"
          value={TIER_LABELS[data.subscriptionTier]}
        />
        <SummaryCard
          icon={<Users className="w-5 h-5" aria-hidden="true" />}
          label="Team invites sent"
          value={sentInvites > 0 ? `${sentInvites} member${sentInvites !== 1 ? "s" : ""}` : "None yet"}
        />
      </motion.div>

      {/* CTA */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: lottieComplete ? 1 : 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
        className="mt-8 w-full"
      >
        <Button
          type="button"
          size="lg"
          className="w-full"
          rightIcon={<ArrowRight className="w-4 h-4" aria-hidden="true" />}
          onClick={handleGoToDashboard}
        >
          Go to Dashboard
        </Button>
      </motion.div>
    </div>
  );
}
