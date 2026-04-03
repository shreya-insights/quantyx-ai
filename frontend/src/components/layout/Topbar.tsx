import { useLocation } from "react-router-dom";
import { Sun, Moon, Menu } from "lucide-react";
import { useThemeStore } from "@/stores/theme.store";

const PAGE_TITLES: Record<string, string> = {
  "/dashboard":    "Dashboard",
  "/transactions": "Transactions",
  "/analytics":    "Analytics",
  "/fraud":        "Fraud Monitor",
  "/query-lab":    "Query Lab",
  "/reports":      "Reports",
  "/settings":     "Settings",
};

interface TopbarProps {
  onMenuClick: () => void;
  sidebarOpen: boolean;
}

export default function Topbar({ onMenuClick, sidebarOpen }: TopbarProps) {
  const { pathname } = useLocation();
  const { theme, toggle } = useThemeStore();
  const isDark = theme === "dark";

  const title = PAGE_TITLES[pathname] ?? "Quantyx AI";

  return (
    <header className="h-14 sticky top-0 z-20 topbar-glass border-b border-slate-200/80 dark:border-slate-800/80 flex items-center justify-between px-4 sm:px-6 flex-shrink-0">
      <div className="flex items-center gap-3">
        {/* Hamburger — mobile only */}
        <button
          onClick={onMenuClick}
          aria-label="Open navigation"
          aria-expanded={sidebarOpen}
          aria-controls="main-sidebar"
          className="lg:hidden p-2 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <Menu size={20} aria-hidden="true" />
        </button>

        <div>
          <span className="text-sm text-slate-400 dark:text-slate-500">
            Quantyx AI &rsaquo;{" "}
          </span>
          <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            {title}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Dark mode toggle */}
        <button
          onClick={toggle}
          aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
          aria-pressed={isDark}
          className="w-9 h-9 rounded-lg flex items-center justify-center text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          {isDark
            ? <Sun size={18} aria-hidden="true" />
            : <Moon size={18} aria-hidden="true" />
          }
        </button>
      </div>
    </header>
  );
}
