import { ChevronRight } from "lucide-react";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  title:        string;
  subtitle?:    string;
  action?:      React.ReactNode;
  breadcrumb?:  BreadcrumbItem[];
}

export function PageHeader({ title, subtitle, action, breadcrumb }: PageHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-6">
      <div>
        {breadcrumb && breadcrumb.length > 0 && (
          <nav aria-label="Breadcrumb" className="mb-1">
            <ol className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-500">
              {breadcrumb.map((crumb, i) => (
                <li key={i} className="flex items-center gap-1">
                  {i > 0 && <ChevronRight size={11} className="text-slate-400" aria-hidden="true" />}
                  {crumb.href ? (
                    <a href={crumb.href} className="hover:text-slate-700 dark:hover:text-slate-300 transition-colors">
                      {crumb.label}
                    </a>
                  ) : (
                    <span className="text-slate-400 dark:text-slate-500">{crumb.label}</span>
                  )}
                </li>
              ))}
            </ol>
          </nav>
        )}
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{title}</h1>
        {subtitle && (
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>
        )}
      </div>
      {action && (
        <div className="flex items-center gap-2 flex-shrink-0">
          {action}
        </div>
      )}
    </div>
  );
}
