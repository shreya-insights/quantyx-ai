import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  CreditCard,
  TrendingUp,
  ShieldAlert,
  Terminal,
  FileText,
  Settings,
  LogOut,
  X,
  type LucideIcon,
} from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/utils/cn";
import { useAuthStore } from "@/stores/auth.store";
import { ROUTES } from "@/utils/constants";

interface NavItem {
  href:   string;
  icon:   LucideIcon;
  label:  string;
  roles?: Array<"admin" | "analyst" | "viewer">;
}

const NAV_ITEMS: NavItem[] = [
  { href: ROUTES.DASHBOARD,    icon: LayoutDashboard, label: "Dashboard" },
  { href: ROUTES.TRANSACTIONS, icon: CreditCard,      label: "Transactions" },
  { href: ROUTES.ANALYTICS,    icon: TrendingUp,      label: "Analytics" },
  { href: ROUTES.FRAUD,        icon: ShieldAlert,     label: "Fraud Monitor" },
  { href: ROUTES.QUERY_LAB,    icon: Terminal,        label: "Query Lab",  roles: ["admin", "analyst"] },
  { href: ROUTES.REPORTS,      icon: FileText,        label: "Reports",    roles: ["admin", "analyst"] },
  { href: ROUTES.SETTINGS,     icon: Settings,        label: "Settings" },
];

interface SidebarProps {
  open:    boolean;
  onClose: () => void;
}

export default function Sidebar({ open, onClose }: SidebarProps) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate(ROUTES.LOGIN);
  };

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.roles || !user?.role || item.roles.includes(user.role)
  );

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        id="main-sidebar"
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex flex-col w-64 bg-slate-900 dark:bg-slate-950 border-r border-slate-800 flex-shrink-0 transition-transform duration-200",
          "lg:static lg:translate-x-0 lg:z-auto lg:h-screen",
          open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Logo row */}
        <div className="px-5 py-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center text-sm font-bold text-white shadow-lg shadow-brand-600/30 dark:shadow-brand-600/20 flex-shrink-0 select-none">
              Q
            </div>
            <div>
              <span className="font-bold text-white text-sm">Quantyx AI</span>
              <div className="text-xs text-slate-400 leading-none mt-0.5">Financial Analytics</div>
            </div>
          </div>
          {/* Mobile close button */}
          <button
            onClick={onClose}
            aria-label="Close navigation"
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        {/* Navigation */}
        <nav aria-label="Main navigation" className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-3 mb-2">
            Main
          </p>
          {visibleItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.href}
                to={item.href}
                onClick={() => onClose()}
                className={({ isActive }) =>
                  cn(
                    "relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 group",
                    isActive
                      ? "text-brand-400"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {/* Animated background pill — slides between items */}
                    {isActive && (
                      <motion.span
                        layoutId="sidebar-pill"
                        className="absolute inset-0 rounded-lg bg-brand-600/20 border border-brand-600/30"
                        transition={{ type: "spring", stiffness: 400, damping: 35 }}
                        aria-hidden="true"
                      />
                    )}
                    <span className="relative flex items-center gap-3">
                      <Icon
                        size={18}
                        strokeWidth={1.75}
                        aria-hidden="true"
                        className="transition-transform duration-150 group-hover:scale-110 flex-shrink-0"
                      />
                      {item.label}
                    </span>
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* User section */}
        <div className="px-3 py-3 border-t border-slate-800">
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg mb-1">
            <div className="w-8 h-8 bg-gradient-to-br from-brand-500 to-violet-600 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0 select-none">
              {user?.full_name?.[0]?.toUpperCase() ?? user?.email?.[0]?.toUpperCase() ?? "U"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-200 truncate">
                {user?.full_name ?? "User"}
              </p>
              <p className="text-xs text-slate-500 truncate capitalize">{user?.role}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors group"
          >
            <LogOut size={16} strokeWidth={1.75} aria-hidden="true" className="transition-transform duration-150 group-hover:scale-110" />
            Sign Out
          </button>
        </div>
      </aside>
    </>
  );
}
