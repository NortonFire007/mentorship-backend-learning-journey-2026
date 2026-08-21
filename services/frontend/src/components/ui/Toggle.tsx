import type { ButtonHTMLAttributes, ReactNode } from "react";

export interface ToggleProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: ReactNode;
  label: string;
}

export function Toggle({ icon, label, className = "", ...props }: ToggleProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={`inline-flex items-center justify-center p-2 rounded-lg text-muted hover:text-foreground hover:bg-surface-hover transition-colors cursor-pointer border border-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${className}`}
      {...props}
    >
      {icon}
    </button>
  );
}
