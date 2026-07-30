"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";

export default function AuthProvider({ children }: { children: ReactNode }) {
  const { silentRefresh } = useAuth();
  const [isInitialized, setIsInitialized] = useState(false);

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

  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return <>{children}</>;
}
