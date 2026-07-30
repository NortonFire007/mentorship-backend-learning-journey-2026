import { ChevronDown } from "lucide-react";
import type { SelectHTMLAttributes } from "react";
import { forwardRef, useId } from "react";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  error?: string;
  helperText?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    { label, options, error, helperText, className = "", id, ...props },
    ref,
  ) => {
    const generatedId = useId();
    const selectId = id || generatedId;
    const errorId = `${selectId}-error`;
    const helperId = `${selectId}-helper`;

    return (
      <div className="w-full flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={selectId}
            className="text-sm font-medium text-foreground"
          >
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          <select
            ref={ref}
            id={selectId}
            aria-invalid={!!error}
            aria-describedby={
              error ? errorId : helperText ? helperId : undefined
            }
            className={`w-full h-10 rounded-lg border bg-surface px-3 pr-10 text-sm text-foreground appearance-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:opacity-50 transition-colors cursor-pointer ${
              error ? "border-error focus:ring-error" : "border-border"
            } ${className}`}
            {...props}
          >
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 h-4 w-4 text-muted pointer-events-none" />
        </div>
        {error && (
          <p id={errorId} className="text-xs text-error font-medium">
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id={helperId} className="text-xs text-muted">
            {helperText}
          </p>
        )}
      </div>
    );
  },
);

Select.displayName = "Select";
