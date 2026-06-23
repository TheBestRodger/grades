import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getNotifications,
  getNotificationUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
} from "../../api";
import { queryKeys } from "../../shared/queryKeys";

export function useNotifications(selectedUserId: number | null) {
  const queryClient = useQueryClient();
  const enabled = selectedUserId !== null;

  async function refreshNotifications() {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: queryKeys.notifications(selectedUserId),
      }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.notificationUnreadCount(selectedUserId),
      }),
    ]);
  }

  const notifications = useQuery({
    queryKey: queryKeys.notifications(selectedUserId),
    queryFn: () => getNotifications(selectedUserId!),
    enabled,
    refetchInterval: 30_000,
  });

  const notificationUnreadCount = useQuery({
    queryKey: queryKeys.notificationUnreadCount(selectedUserId),
    queryFn: () => getNotificationUnreadCount(selectedUserId!),
    enabled,
    refetchInterval: 30_000,
  });

  const markNotificationReadMutation = useMutation({
    mutationFn: (notificationId: number) =>
      markNotificationRead(selectedUserId!, notificationId),
    onSuccess: refreshNotifications,
  });

  const markAllNotificationsReadMutation = useMutation({
    mutationFn: () => markAllNotificationsRead(selectedUserId!),
    onSuccess: refreshNotifications,
  });

  return {
    notifications,
    notificationUnreadCount,
    markNotificationReadMutation,
    markAllNotificationsReadMutation,
  };
}
