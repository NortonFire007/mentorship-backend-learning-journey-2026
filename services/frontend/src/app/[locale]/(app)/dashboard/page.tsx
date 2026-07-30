"use client";

import { useQuery } from "@tanstack/react-query";
import { Bell, Plus, Sliders } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { AlertFeedItem } from "../../../../components/features/alerts/AlertFeedItem";
import { SubscriptionCard } from "../../../../components/features/subscriptions/SubscriptionCard";
import { Button } from "../../../../components/ui/Button";
import { Skeleton } from "../../../../components/ui/Skeleton";
import { useSubscriptions } from "../../../../hooks/useSubscriptions";
import { fetchLatestAlerts } from "../../../../lib/queries/alerts";
import { queryKeys } from "../../../../lib/queries/keys";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale();

  const { subscriptions, isLoading, toggleStatus, deleteSubscription } =
    useSubscriptions();

  const subscriptionIds = subscriptions.map((s) => s.id);

  const { data: alerts = [], isLoading: isAlertsLoading } = useQuery({
    queryKey: queryKeys.alerts.latest(subscriptionIds),
    queryFn: () => fetchLatestAlerts(subscriptionIds, 10),
    enabled: subscriptionIds.length > 0,
  });

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header CTA */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            {t("title")}
          </h1>
          <p className="text-sm text-muted mt-1">{t("subtitle")}</p>
        </div>
        <Link href={`/${locale}/subscriptions/new`}>
          <Button variant="primary" leftIcon={<Plus className="h-4 w-4" />}>
            {t("newSubscriptionBtn")}
          </Button>
        </Link>
      </div>

      {/* Subscriptions Grid Section */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <Sliders className="h-5 w-5 text-primary" />
          <span>{t("activeSubscriptions")}</span>
        </h2>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <Skeleton className="h-44 w-full rounded-xl" />
            <Skeleton className="h-44 w-full rounded-xl" />
            <Skeleton className="h-44 w-full rounded-xl" />
          </div>
        ) : subscriptions.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border p-8 text-center bg-surface/50">
            <h3 className="font-semibold text-foreground">
              {t("noSubscriptionsTitle")}
            </h3>
            <p className="text-xs text-muted mt-1 mb-4">
              {t("noSubscriptionsDesc")}
            </p>
            <Link href={`/${locale}/subscriptions/new`}>
              <Button variant="secondary" size="sm">
                {t("newSubscriptionBtn")}
              </Button>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {subscriptions.map((sub) => (
              <SubscriptionCard
                key={sub.id}
                subscription={sub}
                onToggleStatus={toggleStatus}
                onDelete={deleteSubscription}
              />
            ))}
          </div>
        )}
      </div>

      {/* Recent Alerts Feed Section */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <Bell className="h-5 w-5 text-primary" />
          <span>{t("recentAlerts")}</span>
        </h2>

        {isAlertsLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full rounded-lg" />
            <Skeleton className="h-16 w-full rounded-lg" />
          </div>
        ) : alerts.length === 0 ? (
          <div className="rounded-xl border border-border p-6 text-center bg-surface/30">
            <p className="text-sm font-medium text-foreground">
              {t("noAlertsTitle")}
            </p>
            <p className="text-xs text-muted mt-1">{t("noAlertsDesc")}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <AlertFeedItem key={alert.id} alert={alert} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
