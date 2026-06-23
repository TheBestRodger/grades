export type NotificationTargetSection =
  | "profile"
  | "structure"
  | "campaigns"
  | "manager-reviews"
  | "hr-reviews"
  | "documents";

export interface NotificationItem {
  id: number;
  notification_type: string;
  title: string;
  message: string;
  entity_type: string | null;
  entity_id: string | null;
  target_section: NotificationTargetSection | null;
  read_at: string | null;
  created_at: string | null;
}

export interface NotificationList {
  items: NotificationItem[];
  unread_count: number;
}

export interface NotificationUnreadCount {
  unread_count: number;
}
