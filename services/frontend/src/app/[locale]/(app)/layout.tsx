import type { ReactNode } from "react";
import { AppShell } from "../../../components/layouts/AppShell";

export default function AppRouteLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
