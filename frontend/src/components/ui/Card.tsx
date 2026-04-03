import { type LucideIcon } from "lucide-react";
import { cn } from "@/utils/cn";
import { useCountUp } from "@/hooks/useCountUp";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function Card({ className, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700",
        "shadow-sm hover:shadow-md dark:shadow-none dark:ring-1 dark:ring-slate-700/60 dark:hover:ring-slate-600",
        "transition-all duration-200",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "px-6 py-4 border-b border-slate-100 dark:border-slate-700",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardTitle({ className, children, ...props }: CardProps) {
  return (
    <h3
      className={cn("text-base font-semibold text-slate-900 dark:text-slate-100", className)}
      {...props}
    >
      {children}
    </h3>
  );
}

export function CardContent({ className, children, ...props }: CardProps) {
  return (
    <div className={cn("px-6 py-4", className)} {...props}>
      {children}
    </div>
  );
}

interface StatCardProps {
  title:       string;
  /** Pre-formatted display string (fallback when rawValue is absent) */
  value:       string;
  /** Raw numeric value — triggers count-up animation on mount */
  rawValue?:   number;
  subtitle?:   string;
  icon:        LucideIcon;
  trend?:      string;
  trendUp?:    boolean;
  colorClass?: string;
  iconClass?:  string;
}

/**
 * Formats a raw numeric value the same way as the pre-formatted `value` string.
 * We detect the format by checking the first char of the original string.
 */
function formatAnimated(raw: number, sample: string): string {
  if (sample.startsWith("$")) {
    // currency — simple $X,XXX format
    return `$${raw.toLocaleString("en-US")}`;
  }
  if (sample.endsWith("%")) {
    // keep raw % as-is (count-up for % doesn't apply to decimals)
    return sample;
  }
  return raw.toLocaleString("en-US");
}

export function StatCard({
  title,
  value,
  rawValue,
  subtitle,
  icon: Icon,
  trend,
  trendUp,
  colorClass = "bg-blue-50 border-blue-100 dark:bg-blue-900/10 dark:border-blue-900/30",
  iconClass  = "text-brand-500 dark:text-brand-400",
}: StatCardProps) {
  const prefersReduced = typeof window !== "undefined"
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false;

  const animated = useCountUp(rawValue ?? 0, 900, !prefersReduced && rawValue !== undefined);
  const displayValue = rawValue !== undefined
    ? formatAnimated(animated, value)
    : value;

  return (
    <div
      className={cn(
        "rounded-xl border p-5",
        "transition-all duration-200 hover:-translate-y-1 hover:shadow-lg",
        "cursor-default select-none",
        colorClass
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div className={cn("p-2 rounded-lg bg-white/60 dark:bg-slate-900/40 transition-transform duration-150 group-hover:scale-110", iconClass)}>
          <Icon size={18} strokeWidth={1.75} aria-hidden="true" />
        </div>
        {trend && (
          <span
            className={cn(
              "text-xs font-semibold px-2 py-0.5 rounded-full",
              trendUp
                ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
            )}
          >
            {trend}
          </span>
        )}
      </div>
      <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-0.5">{title}</p>
      <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight tabular-nums">
        {displayValue}
      </p>
      {subtitle && (
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">{subtitle}</p>
      )}
    </div>
  );
}
