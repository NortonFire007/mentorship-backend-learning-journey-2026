import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { RegisterForm } from "../../../../components/features/auth/RegisterForm";

export default async function RegisterPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations("auth");

  return (
    <div className="space-y-6">
      <div className="space-y-1 text-center">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          {t("registerTitle")}
        </h1>
        <p className="text-sm text-muted">{t("registerSubtitle")}</p>
      </div>

      <RegisterForm />

      <div className="text-center text-sm text-muted">
        <span>{t("hasAccount")} </span>
        <Link
          href={`/${locale}/login`}
          className="font-semibold text-primary hover:underline"
        >
          {t("signInLink")}
        </Link>
      </div>
    </div>
  );
}
