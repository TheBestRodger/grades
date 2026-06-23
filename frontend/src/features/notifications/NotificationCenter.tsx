import { useState } from "react";

import type { NotificationItem, NotificationTargetSection } from "../../types";

interface NotificationCenterProps {
  items: NotificationItem[];
  unreadCount: number;
  isLoading: boolean;
  isMarkingAll: boolean;
  onMarkAllRead: () => void;
  onMarkRead: (notificationId: number) => void;
  onNavigate: (section: NotificationTargetSection) => void;
}

function notificationDate(value: string | null): string {
  if (!value) return "";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function NotificationCenter({
  items,
  unreadCount,
  isLoading,
  isMarkingAll,
  onMarkAllRead,
  onMarkRead,
  onNavigate,
}: NotificationCenterProps) {
  const [isOpen, setIsOpen] = useState(false);

  function openNotification(notification: NotificationItem) {
    if (!notification.read_at) onMarkRead(notification.id);
    if (notification.target_section) {
      onNavigate(notification.target_section);
      setIsOpen(false);
    }
  }

  return (
    <div className="relative">
      <button
        aria-expanded={isOpen}
        aria-label={`Уведомления, непрочитанных: ${unreadCount}`}
        className="relative flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 hover:border-blue-300 hover:bg-blue-50"
        onClick={() => setIsOpen((value) => !value)}
        title="Уведомления"
        type="button"
      >
        <span>Уведомления</span>
        {unreadCount > 0 && (
          <span className="min-w-5 rounded-full bg-red-600 px-1.5 py-0.5 text-center text-[10px] font-bold text-white">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 z-30 mt-2 w-[min(420px,calc(100vw-2rem))] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl">
          <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
            <div>
              <p className="font-semibold text-slate-950">Уведомления</p>
              <p className="text-xs text-slate-500">Непрочитанных: {unreadCount}</p>
            </div>
            <button
              className="text-xs font-semibold text-blue-800 disabled:text-slate-400"
              disabled={unreadCount === 0 || isMarkingAll}
              onClick={onMarkAllRead}
              type="button"
            >
              {isMarkingAll ? "Отмечаю..." : "Прочитать все"}
            </button>
          </div>

          <div className="max-h-[420px] overflow-y-auto">
            {isLoading && (
              <p className="px-4 py-6 text-sm text-slate-500">Загружаю уведомления...</p>
            )}
            {!isLoading && items.length === 0 && (
              <p className="px-4 py-6 text-sm text-slate-500">Новых событий пока нет.</p>
            )}
            {items.map((notification) => (
              <button
                className={`block w-full border-b border-slate-100 px-4 py-3 text-left last:border-b-0 ${
                  notification.read_at
                    ? "bg-white hover:bg-slate-50"
                    : "bg-blue-50 hover:bg-blue-100"
                }`}
                key={notification.id}
                onClick={() => openNotification(notification)}
                type="button"
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold text-slate-950">{notification.title}</p>
                  <time className="shrink-0 text-[11px] text-slate-400">
                    {notificationDate(notification.created_at)}
                  </time>
                </div>
                <p className="mt-1 text-sm leading-5 text-slate-600">{notification.message}</p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
