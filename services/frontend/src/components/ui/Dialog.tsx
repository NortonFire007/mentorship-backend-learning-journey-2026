import { X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect } from "react";

export interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children?: ReactNode;
  footer?: ReactNode;
}

export function Dialog({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
}: DialogProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      aria-modal="true"
      role="dialog"
      className="fixed inset-0 flex items-center justify-center p-4 z-[var(--z-modal)]"
    >
      {/* Backdrop */}
      <button
        type="button"
        tabIndex={-1}
        aria-label="Close dialog"
        className="fixed inset-0 bg-black/50 backdrop-blur-xs transition-opacity w-full h-full cursor-default"
        onClick={onClose}
      />

      {/* Content Card */}
      <div className="relative w-full max-w-lg rounded-xl border border-border bg-surface p-6 shadow-xl z-10 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground">{title}</h2>
            {description && (
              <p className="text-sm text-muted mt-1">{description}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-lg p-1 text-muted hover:text-foreground hover:bg-surface-hover transition-colors cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {children && <div className="py-2">{children}</div>}

        {footer && (
          <div className="flex items-center justify-end gap-3 mt-6">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
