import { Badge } from "../../ui/Badge";

export interface SubscriptionStatusBadgeProps {
  isActive: boolean;
}

export function SubscriptionStatusBadge({
  isActive,
}: SubscriptionStatusBadgeProps) {
  return (
    <Badge variant={isActive ? "success" : "muted"}>
      <span
        className={`mr-1.5 h-2 w-2 rounded-full ${
          isActive ? "bg-success animate-pulse" : "bg-muted"
        }`}
      />
      {isActive ? "Active" : "Paused"}
    </Badge>
  );
}
