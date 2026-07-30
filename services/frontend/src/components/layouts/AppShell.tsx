"use client";

import {
  Globe,
  LayoutDashboard,
  LogOut,
  Moon,
  Plane,
  PlusCircle,
  Settings,
  Sun,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { useAuth } from "../../hooks/useAuth";
import { useAuthStore } from "../../stores/authStore";
import { useUiStore } from "../../stores/uiStore";
import { Toggle } from "../ui/Toggle";

export interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const router = useRouter();
  const currentLocale = useLocale();

  const { theme, setTheme } = useUiStore();
  const { user } = useAuthStore();
  const { logout } = useAuth();

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
  };

  const switchLocale = () => {
    const nextLocale = currentLocale === "en" ? "uk" : "en";
    const newPath = pathname.replace(`/${currentLocale}`, `/${nextLocale}`);
    router.push(newPath);
  };

  const handleLogout = async () => {
    await logout();
  };

  const navItems = [
    {
      href: `/${currentLocale}/dashboard`,
      label: t("dashboard"),
      icon: <LayoutDashboard className="h-5 w-5" />,
    },
    {
      href: `/${currentLocale}/subscriptions/new`,
      label: t("newSubscription"),
      icon: <PlusCircle className="h-5 w-5" />,
    },
    {
      href: `/${currentLocale}/settings`,
      label: t("settings"),
      icon: <Settings className="h-5 w-5" />,
    },
  ];

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-background">
      {/* Sidebar Navigation */}
      <aside className="w-full md:w-64 border-b md:border-b-0 md:border-r border-border bg-surface flex flex-col justify-between p-4 shrink-0">
        <div className="space-y-6">
          {/* Logo Brand */}
          <div className="flex items-center gap-2.5 px-2 text-primary font-bold text-lg">
            <Plane className="h-6 w-6" />
            <span>Travel Tracker</span>
          </div>

          {/* Nav Links */}
          <nav className="flex flex-col gap-1">
            {navItems.map((item) => {
              const isActive = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted hover:text-foreground hover:bg-surface-hover"
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer (User info & Logout) */}
        <div className="pt-4 border-t border-border flex items-center justify-between gap-2">
          {user && (
            <div className="truncate text-xs text-muted">
              <p className="font-semibold text-foreground truncate">
                {user.name} {user.surname}
              </p>
              <p className="truncate">{user.email}</p>
            </div>
          )}
          <Toggle
            icon={<LogOut className="h-5 w-5 text-error" />}
            label={t("logout")}
            onClick={handleLogout}
          />
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="h-16 border-b border-border bg-surface px-6 flex items-center justify-end gap-3 shrink-0">
          {/* Theme Toggle */}
          <Toggle
            icon={
              theme === "dark" ? (
                <Sun className="h-5 w-5 text-warning" />
              ) : (
                <Moon className="h-5 w-5 text-muted" />
              )
            }
            label="Toggle Theme"
            onClick={toggleTheme}
          />

          {/* Language Toggle */}
          <Toggle
            icon={
              <div className="flex items-center gap-1 text-xs font-semibold">
                <Globe className="h-4 w-4" />
                <span className="uppercase">{currentLocale}</span>
              </div>
            }
            label="Switch Language"
            onClick={switchLocale}
          />
        </header>

        {/* Page Content */}
        <main className="flex-1 p-6 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
