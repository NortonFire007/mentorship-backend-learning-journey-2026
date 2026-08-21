import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronDown, DollarSign } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import {
  type Step3Input,
  subscriptionStep3Schema,
} from "../../../lib/schemas/subscriptionStep3Schema";
import { Button } from "../../ui/Button";
import { Input } from "../../ui/Input";
import { Select } from "../../ui/Select";

export interface WizardStep3Props {
  initialData: Partial<Step3Input>;
  onSubmit: (data: Step3Input) => void;
  onBack: () => void;
  isSubmitting?: boolean;
  submitError?: string | null;
}

export function WizardStep3({
  initialData,
  onSubmit,
  onBack,
  isSubmitting = false,
  submitError = null,
}: WizardStep3Props) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(subscriptionStep3Schema),
    defaultValues: {
      max_price: initialData.max_price ?? 500,
      currency: initialData.currency || "USD",
      min_bedrooms: initialData.min_bedrooms ?? null,
      min_beds: initialData.min_beds ?? null,
      max_stops: initialData.max_stops ?? null,
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {submitError && (
        <div className="p-3 rounded-lg bg-error/15 text-error text-sm font-medium border border-error/30">
          {submitError}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="sm:col-span-2">
          <Input
            label="Maximum Price"
            type="number"
            min={1}
            leftIcon={<DollarSign className="h-4 w-4" />}
            error={errors.max_price?.message}
            {...register("max_price", { valueAsNumber: true })}
          />
        </div>
        <div>
          <Select
            label="Currency"
            options={[
              { value: "USD", label: "USD ($)" },
              { value: "EUR", label: "EUR (€)" },
              { value: "UAH", label: "UAH (₴)" },
            ]}
            error={errors.currency?.message}
            {...register("currency")}
          />
        </div>
      </div>

      {/* Advanced Accordion Toggle */}
      <div className="border border-border rounded-lg overflow-hidden">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="w-full flex items-center justify-between p-3 bg-surface hover:bg-surface-hover text-sm font-medium text-foreground cursor-pointer"
        >
          <span>Advanced Filters</span>
          <ChevronDown
            className={`h-4 w-4 text-muted transition-transform ${
              showAdvanced ? "rotate-180" : ""
            }`}
          />
        </button>

        {showAdvanced && (
          <div className="p-4 space-y-4 border-t border-border bg-background">
            <div className="grid grid-cols-3 gap-3">
              <Input
                label="Min Bedrooms"
                type="number"
                min={0}
                error={errors.min_bedrooms?.message}
                {...register("min_bedrooms", { valueAsNumber: true })}
              />
              <Input
                label="Min Beds"
                type="number"
                min={0}
                error={errors.min_beds?.message}
                {...register("min_beds", { valueAsNumber: true })}
              />
              <Input
                label="Max Stops"
                type="number"
                min={0}
                error={errors.max_stops?.message}
                {...register("max_stops", { valueAsNumber: true })}
              />
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-border">
        <Button type="button" variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button type="submit" variant="primary" isLoading={isSubmitting}>
          Create Subscription
        </Button>
      </div>
    </form>
  );
}
