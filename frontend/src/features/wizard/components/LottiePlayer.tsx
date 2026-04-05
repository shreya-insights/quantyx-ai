import { useState, useEffect, type ReactNode } from "react";
import { useLottie } from "lottie-react";
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
 * Renders Lottie via `useLottie` (named export). Do not use `import Lottie from
 * "lottie-react"` — Vite/Rolldown can expose the default as a module object, which
 * triggers "Element type is invalid ... got: object".
 */
function LottieCanvas({
  animationData,
  loop,
  autoplay,
  className,
  onComplete,
}: {
  animationData: object;
  loop: boolean;
  autoplay: boolean;
  className?: string;
  onComplete?: () => void;
}) {
  const { View } = useLottie(
    {
      animationData,
      loop,
      autoplay,
      onComplete,
      className,
      rendererSettings: { preserveAspectRatio: "xMidYMid slice" },
    },
    undefined,
  );
  return View;
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

  useEffect(() => {
    setAnimData(null);
    let cancelled = false;
    fetch(src)
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const ct = r.headers.get("content-type") ?? "";
        if (ct.includes("text/html")) {
          throw new Error(
            "Lottie URL returned HTML — asset missing or dev server served index.html",
          );
        }
        return r.json() as Promise<object>;
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
    <LottieCanvas
      animationData={animData}
      loop={loop}
      autoplay={autoplay}
      className={className}
      onComplete={onComplete}
    />
  );
}
