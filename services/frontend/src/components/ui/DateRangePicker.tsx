import { Calendar as CalendarIcon } from "lucide-react";
import type { ChangeEvent } from "react";
import { Input } from "./Input";

export interface DateRangePickerProps {
  startDate?: string | null;
  endDate?: string | null;
  onChange: (range: {
    startDate: string | null;
    endDate: string | null;
  }) => void;
  label?: string;
  error?: string;
}

export function DateRangePicker({
  startDate = "",
  endDate = "",
  onChange,
  label,
  error,
}: DateRangePickerProps) {
  const handleStartChange = (e: ChangeEvent<HTMLInputElement>) => {
    const newStart = e.target.value || null;
    onChange({ startDate: newStart, endDate: endDate || null });
  };

  const handleEndChange = (e: ChangeEvent<HTMLInputElement>) => {
    const newEnd = e.target.value || null;
    onChange({ startDate: startDate || null, endDate: newEnd });
  };

  return (
    <div className="w-full flex flex-col gap-1.5">
      {label && (
        <span className="text-sm font-medium text-foreground">{label}</span>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Input
          type="date"
          value={startDate || ""}
          onChange={handleStartChange}
          leftIcon={<CalendarIcon className="h-4 w-4" />}
          placeholder="Start date"
        />
        <Input
          type="date"
          value={endDate || ""}
          onChange={handleEndChange}
          min={startDate || undefined}
          leftIcon={<CalendarIcon className="h-4 w-4" />}
          placeholder="End date"
        />
      </div>
      {error && <p className="text-xs text-error font-medium">{error}</p>}
    </div>
  );
}
