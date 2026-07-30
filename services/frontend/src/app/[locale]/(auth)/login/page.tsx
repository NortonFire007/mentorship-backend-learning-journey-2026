import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { LoginForm } from "../../../../components/features/auth/LoginForm";

export default async function LoginPage({
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
          {t("loginTitle")}
        </h1>
        <p className="text-sm text-muted">{t("loginSubtitle")}</p>
      </div>

      <LoginForm />

      <div className="text-center text-sm text-muted">
        <span>{t("noAccount")} </span>
        <Link
          href={`/${locale}/register`}
          className="font-semibold text-primary hover:underline"
        >
          {t("signUpLink")}
        </Link>
      </div>
    </div>
  );
}
