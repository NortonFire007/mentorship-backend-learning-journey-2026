import { zodResolver } from "@hookform/resolvers/zod";
import { Minus, Plus } from "lucide-react";
import { useForm } from "react-hook-form";
import {
  type Step2Input,
  subscriptionStep2Schema,
} from "../../../lib/schemas/subscriptionStep2Schema";
import { Button } from "../../ui/Button";
import { DateRangePicker } from "../../ui/DateRangePicker";
import { Input } from "../../ui/Input";

export interface WizardStep2Props {
  initialData: Partial<Step2Input>;
  onNext: (data: Step2Input) => void;
  onBack: () => void;
}

export function WizardStep2({ initialData, onNext, onBack }: WizardStep2Props) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(subscriptionStep2Schema),
    defaultValues: {
      start_date: initialData.start_date || null,
      end_date: initialData.end_date || null,
      adults: initialData.adults ?? 1,
      children: initialData.children ?? 0,
      flexible_days: initialData.flexible_days ?? 0,
    },
  });

  const startDate = watch("start_date");
  const endDate = watch("end_date");
  const adults = Number(watch("adults") ?? 1);
  const children = Number(watch("children") ?? 0);

  return (
    <form onSubmit={handleSubmit(onNext)} className="space-y-6">
      <DateRangePicker
        label="Travel Dates (Optional)"
        startDate={startDate}
        endDate={endDate}
        onChange={({ startDate, endDate }) => {
          setValue("start_date", startDate);
          setValue("end_date", endDate);
        }}
        error={errors.end_date?.message}
      />

      <div className="grid grid-cols-2 gap-4">
        {/* Adults Counter */}
        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-foreground">Adults</span>
          <div className="flex items-center gap-3 border border-border rounded-lg p-1.5 justify-between">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setValue("adults", Math.max(1, adults - 1))}
              disabled={adults <= 1}
            >
              <Minus className="h-3.5 w-3.5" />
            </Button>
            <span className="font-semibold text-sm">{adults}</span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setValue("adults", Math.min(16, adults + 1))}
              disabled={adults >= 16}
            >
              <Plus className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>

        {/* Children Counter */}
        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-foreground">Children</span>
          <div className="flex items-center gap-3 border border-border rounded-lg p-1.5 justify-between">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setValue("children", Math.max(0, children - 1))}
              disabled={children <= 0}
            >
              <Minus className="h-3.5 w-3.5" />
            </Button>
            <span className="font-semibold text-sm">{children}</span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setValue("children", Math.min(16, children + 1))}
              disabled={children >= 16}
            >
              <Plus className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>

      <Input
        label="Flexible Days"
        type="number"
        min={0}
        max={14}
        helperText="Number of flexible days around dates"
        error={errors.flexible_days?.message}
        {...register("flexible_days", { valueAsNumber: true })}
      />

      <div className="flex items-center justify-between pt-4 border-t border-border">
        <Button type="button" variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button type="submit" variant="primary">
          Next Step
        </Button>
      </div>
    </form>
  );
}
