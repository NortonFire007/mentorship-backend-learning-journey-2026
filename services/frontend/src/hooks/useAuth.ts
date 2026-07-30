import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useLocale } from "next-intl";
import {
  fetchCurrentUser,
  loginUser,
  logoutUser,
  refreshAuthToken,
  registerUser,
} from "../lib/queries/auth";
import type { LoginInput } from "../lib/schemas/loginSchema";
import type { RegisterInput } from "../lib/schemas/registerSchema";
import { useAuthStore } from "../stores/authStore";

export function useAuth() {
  const router = useRouter();
  const locale = useLocale();
  const { setAuth, clearAuth } = useAuthStore();

  const loginMutation = useMutation({
    mutationFn: async (credentials: LoginInput) => {
      const tokenResponse = await loginUser(credentials);
      useAuthStore.getState().setAccessToken(tokenResponse.access_token);
      const user = await fetchCurrentUser();
      setAuth(tokenResponse.access_token, user);
      return user;
    },
    onSuccess: () => {
      router.push(`/${locale}/dashboard`);
    },
  });

  const registerMutation = useMutation({
    mutationFn: async (data: RegisterInput) => {
      await registerUser(data);
      // Auto-login after registration
      const tokenResponse = await loginUser({
        email: data.email,
        password: data.password,
      });
      useAuthStore.getState().setAccessToken(tokenResponse.access_token);
      const user = await fetchCurrentUser();
      setAuth(tokenResponse.access_token, user);
      return user;
    },
    onSuccess: () => {
      router.push(`/${locale}/dashboard`);
    },
  });

  const logoutMutation = useMutation({
    mutationFn: async () => {
      try {
        await logoutUser();
      } finally {
        clearAuth();
      }
    },
    onSuccess: () => {
      router.push(`/${locale}/login`);
    },
  });

  const silentRefresh = async () => {
    try {
      const tokenResponse = await refreshAuthToken();
      useAuthStore.getState().setAccessToken(tokenResponse.access_token);
      const user = await fetchCurrentUser();
      setAuth(tokenResponse.access_token, user);
      return user;
    } catch {
      clearAuth();
      return null;
    }
  };

  return {
    login: loginMutation.mutateAsync,
    isLoggingIn: loginMutation.isPending,
    loginError: loginMutation.error,

    register: registerMutation.mutateAsync,
    isRegistering: registerMutation.isPending,
    registerError: registerMutation.error,

    logout: logoutMutation.mutateAsync,
    isLoggingOut: logoutMutation.isPending,

    silentRefresh,
  };
}
