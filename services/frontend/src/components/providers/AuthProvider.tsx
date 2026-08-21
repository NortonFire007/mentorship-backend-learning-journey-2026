"use client";

import { usePathname, useRouter } from "next/navigation";
import { useLocale } from "next-intl";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import { useAuthStore } from "../../stores/authStore";

const PUBLIC_ROUTES = ["/login", "/register"];

export default function AuthProvider({ children }: { children: ReactNode }) {
  const { silentRefresh } = useAuth();
  const [isInitialized, setIsInitialized] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const locale = useLocale();

  useEffect(() => {
    let isMounted = true;
    silentRefresh().finally(() => {
      if (isMounted) {
        setIsInitialized(true);
      }
    });
    return () => {
      isMounted = false;
    };
  }, [silentRefresh]);

  useEffect(() => {
    if (!isInitialized) return;

    const pathnameWithoutLocale = pathname.replace(/^\/(en|uk)/, "") || "/";
    const isPublicRoute = PUBLIC_ROUTES.includes(pathnameWithoutLocale);
    const isAuthenticated = !!useAuthStore.getState().accessToken;

    if (!isAuthenticated && !isPublicRoute) {
      router.push(`/${locale}/login`);
    } else if (isAuthenticated && isPublicRoute) {
      router.push(`/${locale}/dashboard`);
    }
  }, [isInitialized, pathname, router, locale]);

  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return <>{children}</>;
}
