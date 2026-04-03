import { Inbox, type LucideIcon } from "lucide-react";
import { cn } from "@/utils/cn";

interface EmptyStateProps {
  icon?:        LucideIcon;
  title:        string;
  description?: string;
  action?:      React.ReactNode;
  className?:   string;
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-16 px-4 text-center", className)}>
      <div className="w-14 h-14 rounded-2xl bg-slate-100 dark:bg-slate-700/60 flex items-center justify-center mb-4">
        <Icon size={28} strokeWidth={1.5} className="text-slate-400 dark:text-slate-500" aria-hidden="true" />
      </div>
      <h3 className="text-base font-semibold text-slate-700 dark:text-slate-300 mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-slate-400 dark:text-slate-500 max-w-sm">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
