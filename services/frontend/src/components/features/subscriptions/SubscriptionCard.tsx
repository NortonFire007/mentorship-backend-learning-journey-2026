import { Calendar, MapPin, Pause, Play, Trash2 } from "lucide-react";
import { useState } from "react";
import type { SubscriptionRead } from "../../../types/api";
import { Button } from "../../ui/Button";
import { Dialog } from "../../ui/Dialog";
import { SubscriptionStatusBadge } from "./SubscriptionStatusBadge";

export interface SubscriptionCardProps {
  subscription: SubscriptionRead;
  onToggleStatus: (id: string, isActive: boolean) => Promise<unknown>;
  onDelete: (id: string) => Promise<unknown>;
}

export function SubscriptionCard({
  subscription,
  onToggleStatus,
  onDelete,
}: SubscriptionCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [isToggling, setIsToggling] = useState(false);

  const handleToggle = async () => {
    setIsToggling(true);
    try {
      await onToggleStatus(subscription.id, !subscription.is_active);
    } finally {
      setIsToggling(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete(subscription.id);
    } finally {
      setIsDeleting(false);
      setIsConfirmOpen(false);
    }
  };

  return (
    <>
      <div className="w-full rounded-xl border border-border bg-surface p-5 shadow-xs transition-shadow hover:shadow-md flex flex-col justify-between gap-4">
        {/* Header: Destination & Badge */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <MapPin className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground text-base">
                {subscription.destination}
              </h3>
              <p className="text-xs text-muted capitalize">
                {subscription.travel_type} • {subscription.provider}
              </p>
            </div>
          </div>
          <SubscriptionStatusBadge isActive={subscription.is_active} />
        </div>

        {/* Details: Dates & Price */}
        <div className="grid grid-cols-2 gap-2 text-xs text-muted py-2 border-y border-border/50">
          <div className="flex items-center gap-1.5">
            <Calendar className="h-4 w-4" />
            <span>
              {subscription.start_date || "Anytime"}
              {subscription.end_date ? ` - ${subscription.end_date}` : ""}
            </span>
          </div>
          <div className="text-right">
            <span className="text-foreground font-bold text-sm">
              {subscription.currency} {subscription.max_price}
            </span>
            <span className="block text-[10px]">Max threshold</span>
          </div>
        </div>

        {/* Actions Footer */}
        <div className="flex items-center justify-between gap-2">
          <Button
            variant="secondary"
            size="sm"
            isLoading={isToggling}
            onClick={handleToggle}
            leftIcon={
              subscription.is_active ? (
                <Pause className="h-3.5 w-3.5" />
              ) : (
                <Play className="h-3.5 w-3.5" />
              )
            }
          >
            {subscription.is_active ? "Pause" : "Activate"}
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsConfirmOpen(true)}
            className="text-error hover:bg-error/10 hover:text-error"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <Dialog
        isOpen={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        title="Delete Subscription?"
        description="This action cannot be undone. You will stop receiving alerts for this destination."
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsConfirmOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              isLoading={isDeleting}
              onClick={handleDelete}
            >
              Confirm Delete
            </Button>
          </>
        }
      />
    </>
  );
}
