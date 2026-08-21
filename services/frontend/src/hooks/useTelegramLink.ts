import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { fetchCurrentUser, startTelegramLink } from "../lib/queries/auth";
import { queryKeys } from "../lib/queries/keys";
import { useAuthStore } from "../stores/authStore";

export function useTelegramLink() {
  const queryClient = useQueryClient();
  const { user, setAuth } = useAuthStore();
  const [telegramUrl, setTelegramUrl] = useState<string | null>(null);

  const startMutation = useMutation({
    mutationFn: startTelegramLink,
    onSuccess: (data) => {
      setTelegramUrl(data.link);
    },
  });

  const pollStatus = async () => {
    try {
      const updatedUser = await fetchCurrentUser();
      const token = useAuthStore.getState().accessToken;
      if (token) {
        setAuth(token, updatedUser);
      }
      queryClient.setQueryData(queryKeys.auth.me(), updatedUser);
      return updatedUser;
    } catch {
      return null;
    }
  };

  return {
    telegramChatId: user?.telegram_chat_id || null,
    telegramUrl,
    isGeneratingLink: startMutation.isPending,
    generateLink: startMutation.mutateAsync,
    pollStatus,
  };
}
