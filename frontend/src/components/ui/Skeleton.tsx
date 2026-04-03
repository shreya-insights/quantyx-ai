import { cn } from "@/utils/cn";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "rounded",
        "bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200",
        "dark:from-slate-700 dark:via-slate-600 dark:to-slate-700",
        "bg-[length:200%_100%] animate-shimmer",
        className
      )}
    />
  );
}

export function KpiCardSkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 space-y-3">
      <Skeleton className="h-8 w-8 rounded-lg" />
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-7 w-32" />
      <Skeleton className="h-3 w-20" />
    </div>
  );
}

export function TableRowSkeleton({ cols = 6 }: { cols?: number }) {
  return (
    <tr className="border-b border-slate-50 dark:border-slate-800">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="py-3 px-4">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  );
}

export function PageSkeleton() {
  return (
    <div className="p-6 lg:p-8">
      <div className="mb-6">
        <Skeleton className="h-7 w-48 mb-2" />
        <Skeleton className="h-4 w-72" />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {Array.from({ length: 8 }).map((_, i) => (
          <KpiCardSkeleton key={i} />
        ))}
      </div>
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <Skeleton className="h-5 w-40 mb-4" />
          <Skeleton className="h-52 w-full rounded-lg" />
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <Skeleton className="h-5 w-40 mb-4" />
          <Skeleton className="h-52 w-full rounded-lg" />
        </div>
      </div>
    </div>
  );
}
