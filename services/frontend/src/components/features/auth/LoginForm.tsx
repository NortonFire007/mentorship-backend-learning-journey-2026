"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Lock, Mail } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useAuth } from "../../../hooks/useAuth";
import { type LoginInput, loginSchema } from "../../../lib/schemas/loginSchema";
import { Button } from "../../ui/Button";
import { Input } from "../../ui/Input";

export function LoginForm() {
  const t = useTranslations("auth");
  const { login, isLoggingIn } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const onSubmit = async (data: LoginInput) => {
    setServerError(null);
    try {
      await login(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setServerError(err.message || t("invalidCredentials"));
      } else {
        setServerError(t("invalidCredentials"));
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {serverError && (
        <div className="p-3 rounded-lg bg-error/15 text-error text-sm font-medium border border-error/30">
          {serverError}
        </div>
      )}

      <Input
        label={t("emailLabel")}
        placeholder={t("emailPlaceholder")}
        type="email"
        autoComplete="email"
        leftIcon={<Mail className="h-4 w-4" />}
        error={errors.email?.message}
        {...register("email")}
      />

      <Input
        label={t("passwordLabel")}
        placeholder={t("passwordPlaceholder")}
        type="password"
        autoComplete="current-password"
        leftIcon={<Lock className="h-4 w-4" />}
        error={errors.password?.message}
        {...register("password")}
      />

      <Button
        type="submit"
        variant="primary"
        size="lg"
        className="w-full mt-2"
        isLoading={isLoggingIn}
      >
        {t("submitLogin")}
      </Button>
    </form>
  );
}
