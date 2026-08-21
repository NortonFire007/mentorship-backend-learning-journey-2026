"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale } from "next-intl";
import { createSubscription } from "../../../lib/queries/subscriptions";
import type { Step1Input } from "../../../lib/schemas/subscriptionStep1Schema";
import type { Step2Input } from "../../../lib/schemas/subscriptionStep2Schema";
import type { Step3Input } from "../../../lib/schemas/subscriptionStep3Schema";
import { useWizardStore } from "../../../stores/uiStore";
import type { SubscriptionCreate } from "../../../types/api";
import { WizardStep1 } from "./WizardStep1";
import { WizardStep2 } from "./WizardStep2";
import { WizardStep3 } from "./WizardStep3";

export function SubscriptionWizard() {
  const router = useRouter();
  const locale = useLocale();
  const queryClient = useQueryClient();
  const { step, data, setStep, updateData, clearWizard } = useWizardStore();

  const createMutation = useMutation({
    mutationFn: (payload: SubscriptionCreate) => createSubscription(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
      clearWizard();
      router.push(`/${locale}/dashboard`);
    },
  });

  const handleStep1Next = (step1Data: Step1Input) => {
    updateData(step1Data);
    setStep(2);
  };

  const handleStep2Next = (step2Data: Step2Input) => {
    updateData(step2Data);
    setStep(3);
  };

  const handleStep3Submit = (step3Data: Step3Input) => {
    const finalPayload: SubscriptionCreate = {
      destination: data.destination || "",
      travel_type: data.travel_type || "flight",
      provider: data.provider || "apify_airbnb",
      start_date: data.start_date || null,
      end_date: data.end_date || null,
      adults: data.adults ?? 1,
      children: data.children ?? 0,
      flexible_days: data.flexible_days ?? 0,
      max_price: step3Data.max_price,
      currency: step3Data.currency,
      min_bedrooms: step3Data.min_bedrooms || null,
      min_beds: step3Data.min_beds || null,
      max_stops: step3Data.max_stops || null,
    };
    createMutation.mutate(finalPayload);
  };

  const steps = [
    { title: "Destination & Type", number: 1 },
    { title: "Dates & Travelers", number: 2 },
    { title: "Budget & Filters", number: 3 },
  ];

  return (
    <div className="w-full max-w-xl mx-auto rounded-2xl border border-border bg-surface p-6 sm:p-8 shadow-sm">
      {/* Progress Steps Header */}
      <div className="flex items-center justify-between mb-8 relative">
        {steps.map((s, idx) => {
          const isDone = step > s.number;
          const isCurrent = step === s.number;
          return (
            <div key={s.number} className="flex items-center gap-2 z-10">
              <div
                className={`h-8 w-8 rounded-full flex items-center justify-center font-bold text-xs transition-colors ${
                  isDone
                    ? "bg-success text-success-foreground"
                    : isCurrent
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted-background text-muted border border-border"
                }`}
              >
                {isDone ? <Check className="h-4 w-4" /> : s.number}
              </div>
              <span
                className={`hidden sm:inline text-xs font-medium ${
                  isCurrent ? "text-foreground font-semibold" : "text-muted"
                }`}
              >
                {s.title}
              </span>
              {idx < steps.length - 1 && (
                <div className="hidden sm:block h-[1px] w-8 bg-border ml-2" />
              )}
            </div>
          );
        })}
      </div>

      {/* Step Content */}
      {step === 1 && (
        <WizardStep1 initialData={data} onNext={handleStep1Next} />
      )}
      {step === 2 && (
        <WizardStep2
          initialData={data}
          onNext={handleStep2Next}
          onBack={() => setStep(1)}
        />
      )}
      {step === 3 && (
        <WizardStep3
          initialData={data}
          onSubmit={handleStep3Submit}
          onBack={() => setStep(2)}
          isSubmitting={createMutation.isPending}
          submitError={
            createMutation.error
              ? (createMutation.error as Error).message
              : null
          }
        />
      )}
    </div>
  );
}
