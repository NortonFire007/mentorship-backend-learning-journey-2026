import type { AlertStatus } from "../../../types/api";
import { Badge, type BadgeVariant } from "../../ui/Badge";

export interface AlertStatusBadgeProps {
  status: AlertStatus;
}

export function AlertStatusBadge({ status }: AlertStatusBadgeProps) {
  const variantMap: Record<AlertStatus, BadgeVariant> = {
    SENT: "success",
    PENDING: "warning",
    FAILED: "error",
    SKIPPED: "muted",
  };

  return <Badge variant={variantMap[status]}>{status}</Badge>;
}
