import { cn } from "@/utils/cn";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "info" | "purple";

interface BadgeProps {
  children:  React.ReactNode;
  variant?:  BadgeVariant;
  className?: string;
  dot?:      boolean;
}

const variants: Record<BadgeVariant, string> = {
  default: "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300",
  success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  warning: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  danger:  "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  info:    "bg-brand-100 text-brand-800 dark:bg-brand-900/40 dark:text-brand-300",
  purple:  "bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300",
};

export function Badge({ children, variant = "default", className, dot = false }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
        variants[variant],
        className
      )}
    >
      {dot && (
        <span
          className="w-1.5 h-1.5 rounded-full bg-current mr-1.5 inline-block flex-shrink-0"
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}
