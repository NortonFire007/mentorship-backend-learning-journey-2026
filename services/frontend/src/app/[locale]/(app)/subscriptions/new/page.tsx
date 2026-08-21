import { getTranslations } from "next-intl/server";
import { SubscriptionWizard } from "../../../../../components/features/subscriptions/SubscriptionWizard";

export default async function NewSubscriptionPage() {
  const t = await getTranslations("subscription.wizard");

  return (
    <div className="space-y-6 max-w-4xl mx-auto py-4">
      <div className="text-center space-y-1">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          {t("step1Title")}
        </h1>
        <p className="text-sm text-muted">{t("step1Subtitle")}</p>
      </div>

      <SubscriptionWizard />
    </div>
  );
}
