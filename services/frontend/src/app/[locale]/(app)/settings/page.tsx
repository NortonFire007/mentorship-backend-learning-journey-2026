"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Lock, User } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { TelegramConnectBlock } from "../../../../components/features/telegram/TelegramConnectBlock";
import { McpTokenBlock } from "../../../../components/features/mcp/McpTokenBlock";
import { Button } from "../../../../components/ui/Button";
import { Input } from "../../../../components/ui/Input";
import { Select } from "../../../../components/ui/Select";
import { useAuth } from "../../../../hooks/useAuth";
import { apiClient } from "../../../../lib/clients/api";
import { queryKeys } from "../../../../lib/queries/keys";
import {
  type ChangePasswordInput,
  changePasswordSchema,
} from "../../../../lib/schemas/changePasswordSchema";
import {
  type ProfileInput,
  profileSchema,
} from "../../../../lib/schemas/profileSchema";
import { useAuthStore } from "../../../../stores/authStore";
import type { UserRead } from "../../../../types/api";

export default function SettingsPage() {
  const { user, setAuth } = useAuthStore();
  const { logout } = useAuth();
  const queryClient = useQueryClient();

  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // Profile Form
  const {
    register: registerProfile,
    handleSubmit: handleProfileSubmit,
    formState: { errors: profileErrors },
  } = useForm<ProfileInput>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      name: user?.name || "",
      surname: user?.surname || "",
      preferred_currency: user?.preferred_currency || "USD",
    },
  });

  const updateProfileMutation = useMutation({
    mutationFn: async (payload: ProfileInput) => {
      return apiClient<UserRead>("/api/v1/auth/me", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    onSuccess: (updatedUser) => {
      const token = useAuthStore.getState().accessToken;
      if (token) {
        setAuth(token, updatedUser);
      }
      queryClient.setQueryData(queryKeys.auth.me(), updatedUser);
      setProfileSuccess("Profile updated successfully!");
      setTimeout(() => setProfileSuccess(null), 4000);
    },
  });

  // Password Form
  const {
    register: registerPassword,
    handleSubmit: handlePasswordSubmit,
    reset: resetPasswordForm,
    formState: { errors: passwordErrors },
  } = useForm<ChangePasswordInput>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: {
      old_password: "",
      new_password: "",
      confirm_password: "",
    },
  });

  const changePasswordMutation = useMutation({
    mutationFn: async (payload: ChangePasswordInput) => {
      return apiClient<void>("/api/v1/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          old_password: payload.old_password,
          new_password: payload.new_password,
        }),
      });
    },
    onSuccess: () => {
      setPasswordError(null);
      setPasswordSuccess(
        "Password changed successfully! Logging out in 2 seconds...",
      );
      resetPasswordForm();
      setTimeout(() => {
        logout();
      }, 2000);
    },
    onError: (err: Error) => {
      setPasswordError(err.message || "Failed to change password.");
    },
  });

  return (
    <div className="space-y-8 max-w-3xl mx-auto py-2">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Account Settings
        </h1>
        <p className="text-sm text-muted mt-1">
          Manage your personal details, security settings, and alert
          notifications.
        </p>
      </div>

      {/* Telegram Section */}
      <div className="space-y-3">
        <h2 className="text-base font-semibold text-foreground">
          Notifications
        </h2>
        <TelegramConnectBlock />
      </div>

      {/* MCP Admin Access Section for Superusers */}
      {user?.is_superuser && (
        <div className="space-y-3">
          <h2 className="text-base font-semibold text-foreground">
            Admin & AI Integrations
          </h2>
          <McpTokenBlock />
        </div>
      )}

      {/* Profile Form Section */}
      <div className="rounded-xl border border-border bg-surface p-6 space-y-4">
        <div className="flex items-center gap-2 text-foreground font-semibold text-base">
          <User className="h-5 w-5 text-primary" />
          <span>Personal Information</span>
        </div>

        {profileSuccess && (
          <div className="p-3 rounded-lg bg-success/15 text-success text-sm font-medium border border-success/30">
            {profileSuccess}
          </div>
        )}

        <form
          onSubmit={handleProfileSubmit((data) =>
            updateProfileMutation.mutate(data),
          )}
          className="space-y-4"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="First Name"
              error={profileErrors.name?.message}
              {...registerProfile("name")}
            />
            <Input
              label="Last Name"
              error={profileErrors.surname?.message}
              {...registerProfile("surname")}
            />
          </div>

          <Select
            label="Preferred Currency"
            options={[
              { value: "USD", label: "USD ($)" },
              { value: "EUR", label: "EUR (€)" },
              { value: "UAH", label: "UAH (₴)" },
            ]}
            error={profileErrors.preferred_currency?.message}
            {...registerProfile("preferred_currency")}
          />

          <Button
            type="submit"
            variant="primary"
            isLoading={updateProfileMutation.isPending}
          >
            Save Profile
          </Button>
        </form>
      </div>

      {/* Security / Password Form Section */}
      <div className="rounded-xl border border-border bg-surface p-6 space-y-4">
        <div className="flex items-center gap-2 text-foreground font-semibold text-base">
          <Lock className="h-5 w-5 text-primary" />
          <span>Security & Password</span>
        </div>

        {passwordSuccess && (
          <div className="p-3 rounded-lg bg-success/15 text-success text-sm font-medium border border-success/30">
            {passwordSuccess}
          </div>
        )}

        {passwordError && (
          <div className="p-3 rounded-lg bg-error/15 text-error text-sm font-medium border border-error/30">
            {passwordError}
          </div>
        )}

        <form
          onSubmit={handlePasswordSubmit((data) =>
            changePasswordMutation.mutate(data),
          )}
          className="space-y-4"
        >
          <Input
            label="Current Password"
            type="password"
            error={passwordErrors.old_password?.message}
            {...registerPassword("old_password")}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="New Password"
              type="password"
              error={passwordErrors.new_password?.message}
              {...registerPassword("new_password")}
            />
            <Input
              label="Confirm New Password"
              type="password"
              error={passwordErrors.confirm_password?.message}
              {...registerPassword("confirm_password")}
            />
          </div>

          <Button
            type="submit"
            variant="secondary"
            isLoading={changePasswordMutation.isPending}
          >
            Change Password
          </Button>
        </form>
      </div>
    </div>
  );
}
