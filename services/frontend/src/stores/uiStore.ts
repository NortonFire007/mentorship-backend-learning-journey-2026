import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { SubscriptionCreate } from "../types/api";

export type Theme = "light" | "dark";
export type Locale = "en" | "uk";

interface UiState {
  theme: Theme;
  locale: Locale;
  setTheme: (theme: Theme) => void;
  setLocale: (locale: Locale) => void;
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      theme: "light",
      locale: "en",
      setTheme: (theme) => {
        if (typeof document !== "undefined") {
          document.documentElement.setAttribute("data-theme", theme);
        }
        set({ theme });
      },
      setLocale: (locale) => set({ locale }),
    }),
    {
      name: "ui-storage",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);

interface WizardState {
  step: number;
  data: Partial<SubscriptionCreate>;
  setStep: (step: number) => void;
  updateData: (data: Partial<SubscriptionCreate>) => void;
  clearWizard: () => void;
}

const initialWizardData: Partial<SubscriptionCreate> = {
  destination: "",
  travel_type: "flight",
  provider: "airbnb",
  adults: 1,
  children: 0,
  flexible_days: 0,
  max_price: 500,
  currency: "USD",
};

export const useWizardStore = create<WizardState>()(
  persist(
    (set) => ({
      step: 1,
      data: initialWizardData,
      setStep: (step) => set({ step }),
      updateData: (data) =>
        set((state) => ({ data: { ...state.data, ...data } })),
      clearWizard: () => set({ step: 1, data: initialWizardData }),
    }),
    {
      name: "subscription-wizard-storage",
      storage: createJSONStorage(() => sessionStorage),
    },
  ),
);
