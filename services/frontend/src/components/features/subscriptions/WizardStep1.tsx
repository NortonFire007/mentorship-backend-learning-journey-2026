import { zodResolver } from "@hookform/resolvers/zod";
import { Building, MapPin, Plane } from "lucide-react";
import { useForm } from "react-hook-form";
import {
  type Step1Input,
  subscriptionStep1Schema,
} from "../../../lib/schemas/subscriptionStep1Schema";
import { Button } from "../../ui/Button";
import { Input } from "../../ui/Input";
import { Select } from "../../ui/Select";

export interface WizardStep1Props {
  initialData: Partial<Step1Input>;
  onNext: (data: Step1Input) => void;
}

export function WizardStep1({ initialData, onNext }: WizardStep1Props) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<Step1Input>({
    resolver: zodResolver(subscriptionStep1Schema),
    defaultValues: {
      destination: initialData.destination || "",
      travel_type: initialData.travel_type || "flight",
      provider: initialData.provider || "apify_airbnb",
    },
  });

  const selectedTravelType = watch("travel_type");

  return (
    <form onSubmit={handleSubmit(onNext)} className="space-y-6">
      <Input
        label="Destination"
        placeholder="e.g. Paris, France or Rome"
        leftIcon={<MapPin className="h-4 w-4" />}
        error={errors.destination?.message}
        {...register("destination")}
      />

      {/* Travel Type Selector Tabs */}
      <div className="space-y-2">
        <span className="text-sm font-medium text-foreground">Travel Type</span>
        <div className="grid grid-cols-3 gap-2">
          <button
            type="button"
            onClick={() => setValue("travel_type", "flight")}
            className={`flex flex-col items-center justify-center p-3 rounded-lg border text-xs font-semibold gap-1.5 transition-colors cursor-pointer ${
              selectedTravelType === "flight"
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted hover:bg-surface-hover"
            }`}
          >
            <Plane className="h-5 w-5" />
            <span>Flight</span>
          </button>

          <button
            type="button"
            onClick={() => setValue("travel_type", "hotel")}
            className={`flex flex-col items-center justify-center p-3 rounded-lg border text-xs font-semibold gap-1.5 transition-colors cursor-pointer ${
              selectedTravelType === "hotel"
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted hover:bg-surface-hover"
            }`}
          >
            <Building className="h-5 w-5" />
            <span>Hotel / Apartment</span>
          </button>

          <button
            type="button"
            onClick={() => setValue("travel_type", "package")}
            className={`flex flex-col items-center justify-center p-3 rounded-lg border text-xs font-semibold gap-1.5 transition-colors cursor-pointer ${
              selectedTravelType === "package"
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted hover:bg-surface-hover"
            }`}
          >
            <MapPin className="h-5 w-5" />
            <span>Package</span>
          </button>
        </div>
      </div>

      <Select
        label="Provider"
        options={[
          { value: "apify_airbnb", label: "Airbnb (Active)" },
          { value: "booking", label: "Booking.com (Coming soon)" },
          { value: "skyscanner", label: "Skyscanner (Coming soon)" },
        ]}
        error={errors.provider?.message}
        {...register("provider")}
      />

      <div className="flex justify-end pt-4 border-t border-border">
        <Button type="submit" variant="primary">
          Next Step
        </Button>
      </div>
    </form>
  );
}
