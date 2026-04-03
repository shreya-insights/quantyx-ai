import { useEffect, useRef, useState } from "react";

/**
 * Animates a number from 0 → target using an ease-out cubic curve.
 * Falls back to the target immediately if `enabled` is false (e.g. reduced motion).
 */
export function useCountUp(
  target: number,
  duration = 900,
  enabled = true
): number {
  const [value, setValue] = useState(enabled ? 0 : target);
  const rafRef   = useRef<number>(0);
  const startRef = useRef<number>(0);
  // Track the last target so we reset cleanly when data changes
  const prevTarget = useRef<number>(target);

  useEffect(() => {
    if (!enabled) {
      setValue(target);
      return;
    }

    // Re-start animation whenever target changes
    if (prevTarget.current !== target) {
      setValue(0);
      prevTarget.current = target;
    }

    startRef.current = performance.now();

    const tick = (now: number) => {
      const elapsed  = now - startRef.current;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic: fast start, slow finish
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, duration, enabled]);

  return value;
}
