import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../lib/queries/keys";
import {
  deleteSubscription,
  fetchUserSubscriptions,
  updateSubscription,
} from "../lib/queries/subscriptions";
import { useAuthStore } from "../stores/authStore";
import type { SubscriptionRead } from "../types/api";

export function useSubscriptions() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const userId = user?.id;

  const subscriptionsQuery = useQuery({
    queryKey: queryKeys.subscriptions.list(),
    queryFn: () => (userId ? fetchUserSubscriptions(userId) : []),
    enabled: !!userId,
  });

  const toggleStatusMutation = useMutation({
    mutationFn: async ({ id, isActive }: { id: string; isActive: boolean }) => {
      return updateSubscription(id, { is_active: isActive });
    },
    // Optimistic Update
    onMutate: async ({ id, isActive }) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.subscriptions.list(),
      });

      const previousSubscriptions = queryClient.getQueryData<
        SubscriptionRead[]
      >(queryKeys.subscriptions.list());

      queryClient.setQueryData<SubscriptionRead[]>(
        queryKeys.subscriptions.list(),
        (old) =>
          old?.map((sub) =>
            sub.id === id ? { ...sub, is_active: isActive } : sub,
          ) || [],
      );

      return { previousSubscriptions };
    },
    onError: (_err, _variables, context) => {
      if (context?.previousSubscriptions) {
        queryClient.setQueryData(
          queryKeys.subscriptions.list(),
          context.previousSubscriptions,
        );
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.subscriptions.list(),
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteSubscription(id),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.subscriptions.list(),
      });
    },
  });

  return {
    subscriptions: subscriptionsQuery.data || [],
    isLoading: subscriptionsQuery.isLoading,
    isError: subscriptionsQuery.isError,
    toggleStatus: (id: string, isActive: boolean) =>
      toggleStatusMutation.mutateAsync({ id, isActive }),
    deleteSubscription: (id: string) => deleteMutation.mutateAsync(id),
  };
}
