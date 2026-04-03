import { forwardRef } from "react";
import { cn } from "@/utils/cn";
import { Spinner } from "./Spinner";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline";
type Size    = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:  Variant;
  size?:     Size;
  loading?:  boolean;
  leftIcon?:  React.ReactNode;
  rightIcon?: React.ReactNode;
}

const variants: Record<Variant, string> = {
  primary:   "bg-brand-600 hover:bg-brand-500 active:bg-brand-700 text-white shadow-sm disabled:bg-brand-300",
  secondary: "bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200",
  ghost:     "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300",
  danger:    "bg-red-600 hover:bg-red-500 active:bg-red-700 text-white shadow-sm disabled:bg-red-300",
  outline:   "border border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200",
};

const sizes: Record<Size, string> = {
  sm: "px-3 py-1.5 text-xs gap-1.5",
  md: "px-4 py-2 text-sm gap-2",
  lg: "px-5 py-2.5 text-base gap-2",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      loading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      ...props
    },
    ref
  ) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "relative inline-flex items-center justify-center font-medium rounded-lg transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2",
        "disabled:cursor-not-allowed select-none",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {/* Spinner overlays the content; content stays in flow (invisible) so button width is stable */}
      {loading && (
        <span className="absolute inset-0 flex items-center justify-center">
          <Spinner size="sm" className="text-current" aria-hidden="true" />
        </span>
      )}
      {leftIcon && !loading && leftIcon}
      <span className={cn(loading ? "invisible" : "")}>{children}</span>
      {rightIcon && !loading && rightIcon}
    </button>
  )
);

Button.displayName = "Button";
