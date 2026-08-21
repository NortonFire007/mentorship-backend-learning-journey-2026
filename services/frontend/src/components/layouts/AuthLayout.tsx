import { Plane } from "lucide-react";
import type { ReactNode } from "react";

export interface AuthLayoutProps {
  children: ReactNode;
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 bg-background">
      <div className="w-full max-w-md space-y-6">
        <div className="flex items-center justify-center gap-2 text-primary font-bold text-xl">
          <Plane className="h-6 w-6" />
          <span>Travel Tracker</span>
        </div>
        <div className="w-full rounded-2xl border border-border bg-surface p-8 shadow-sm">
          {children}
        </div>
      </div>
    </div>
  );
}
