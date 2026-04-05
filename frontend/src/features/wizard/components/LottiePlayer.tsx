import { useState, useEffect, useRef, type ReactNode } from "react";
import Lottie, { type LottieRefCurrentProps } from "lottie-react";
import { cn } from "@/utils/cn";

interface LottiePlayerProps {
  src: string;
  loop?: boolean;
  autoplay?: boolean;
  className?: string;
  onComplete?: () => void;
  /** Icon rendered inside a pulsing ring when the Lottie JSON hasn't loaded yet. */
  fallbackIcon?: ReactNode;
}

/**
 * Fetches and renders a Lottie JSON animation.
 * While loading (or when the JSON file is absent), shows a branded icon placeholder
 * rather than a grey skeleton, keeping the UI intentional at every state.
 * onComplete fires once when a non-looping animation finishes.
 */
export function LottiePlayer({
  src,
  loop = true,
  autoplay = true,
  className,
  onComplete,
  fallbackIcon,
}: LottiePlayerProps) {
  const [animData, setAnimData] = useState<object | null>(null);
  const lottieRef = useRef<LottieRefCurrentProps>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(src)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (!cancelled) setAnimData(data);
      })
      .catch((err) => {
        console.warn(`LottiePlayer: could not load ${src}`, err);
      });
    return () => {
      cancelled = true;
    };
  }, [src]);

  if (!animData) {
    return (
      <div
        className={cn("flex items-center justify-center rounded-2xl", className)}
        aria-hidden="true"
      >
        <div className="w-20 h-20 rounded-full bg-white/10 animate-pulse flex items-center justify-center ring-2 ring-white/20">
          {fallbackIcon}
        </div>
      </div>
    );
  }

  return (
    <Lottie
      lottieRef={lottieRef}
      animationData={animData}
      loop={loop}
      autoplay={autoplay}
      onComplete={onComplete}
      className={className}
      rendererSettings={{ preserveAspectRatio: "xMidYMid slice" }}
    />
  );
}
