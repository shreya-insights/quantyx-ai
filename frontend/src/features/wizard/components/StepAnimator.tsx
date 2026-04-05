import { type ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

interface StepAnimatorProps {
  stepKey: number;
  direction: "forward" | "backward";
  children: ReactNode;
}

/** How far the entering/exiting step travels on the x-axis. Subtle — not a full-screen sweep. */
const SLIDE_DISTANCE = 60;

const getVariants = (direction: "forward" | "backward", reduced: boolean) => ({
  initial: reduced
    ? { opacity: 0 }
    : {
        opacity: 0,
        x: direction === "forward" ? SLIDE_DISTANCE : -SLIDE_DISTANCE,
      },
  animate: { opacity: 1, x: 0 },
  exit: reduced
    ? { opacity: 0 }
    : {
        opacity: 0,
        x: direction === "forward" ? -SLIDE_DISTANCE : SLIDE_DISTANCE,
      },
});

/**
 * Wraps a wizard step in a Framer Motion slide/fade transition.
 *
 * Rules applied:
 * - AnimatePresence mode="wait": exit completes before enter starts — no overlap flicker.
 * - initial={false}: suppresses animation on the very first page load.
 * - key={stepKey}: changing key triggers the full exit → enter cycle.
 * - useReducedMotion(): OS accessibility setting respected — falls back to opacity fade.
 * - willChange hint: GPU compositing layer prepared before animation fires.
 */
export function StepAnimator({ stepKey, direction, children }: StepAnimatorProps) {
  const prefersReduced = useReducedMotion();

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={stepKey}
        variants={getVariants(direction, !!prefersReduced)}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={{ duration: 0.35, ease: [0.25, 0.1, 0.25, 1.0] }}
        className="w-full"
        style={{ willChange: "transform, opacity" }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
