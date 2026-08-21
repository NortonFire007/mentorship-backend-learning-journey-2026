"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Lock, Mail, User } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useAuth } from "../../../hooks/useAuth";
import {
  type RegisterInput,
  registerSchema,
} from "../../../lib/schemas/registerSchema";
import { Button } from "../../ui/Button";
import { Input } from "../../ui/Input";

export function RegisterForm() {
  const t = useTranslations("auth");
  const { register: registerAuth, isRegistering } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterInput>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: "",
      surname: "",
      email: "",
      password: "",
    },
  });

  const onSubmit = async (data: RegisterInput) => {
    setServerError(null);
    try {
      await registerAuth(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setServerError(err.message || t("emailInUse"));
      } else {
        setServerError(t("emailInUse"));
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

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Input
          label={t("nameLabel")}
          placeholder={t("namePlaceholder")}
          leftIcon={<User className="h-4 w-4" />}
          error={errors.name?.message}
          {...register("name")}
        />
        <Input
          label={t("surnameLabel")}
          placeholder={t("surnamePlaceholder")}
          leftIcon={<User className="h-4 w-4" />}
          error={errors.surname?.message}
          {...register("surname")}
        />
      </div>

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
        autoComplete="new-password"
        leftIcon={<Lock className="h-4 w-4" />}
        error={errors.password?.message}
        {...register("password")}
      />

      <Button
        type="submit"
        variant="primary"
        size="lg"
        className="w-full mt-2"
        isLoading={isRegistering}
      >
        {t("submitRegister")}
      </Button>
    </form>
  );
}
