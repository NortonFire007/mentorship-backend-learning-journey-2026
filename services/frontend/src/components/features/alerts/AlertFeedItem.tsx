import { ExternalLink, Tag } from "lucide-react";
import type { AlertRead } from "../../../types/api";
import { AlertStatusBadge } from "./AlertStatusBadge";

export interface AlertFeedItemProps {
  alert: AlertRead;
}

export function AlertFeedItem({ alert }: AlertFeedItemProps) {
  const formattedDate = new Date(alert.created_at).toLocaleDateString(
    undefined,
    {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    },
  );

  return (
    <div className="w-full rounded-lg border border-border bg-surface p-4 flex items-center justify-between gap-4 transition-colors hover:bg-surface-hover">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-success/10 text-success">
          <Tag className="h-4 w-4" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-foreground text-sm">
              ${alert.price_found}
            </span>
            <AlertStatusBadge status={alert.status} />
          </div>
          <p className="text-xs text-muted mt-0.5">{formattedDate}</p>
        </div>
      </div>

      {alert.deep_link && (
        <a
          href={alert.deep_link}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
        >
          <span>View listing</span>
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      )}
    </div>
  );
}
