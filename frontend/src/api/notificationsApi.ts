import { request } from "./request";
import { API_URL } from "./urls";
import type {
  NotificationItem,
  NotificationList,
  NotificationUnreadCount,
} from "./types";

export const getNotifications = (userId: number, limit = 50) =>
  request<NotificationList>(API_URL.notifications.list(limit), { userId });

export const getNotificationUnreadCount = (userId: number) =>
  request<NotificationUnreadCount>(API_URL.notifications.unreadCount, { userId });

export const markNotificationRead = (userId: number, notificationId: number) =>
  request<NotificationItem>(API_URL.notifications.read(notificationId), {
    userId,
    method: "POST",
  });

export const markAllNotificationsRead = (userId: number) =>
  request<{ updated: number }>(API_URL.notifications.readAll, {
    userId,
    method: "POST",
  });
