import type { ReactNode } from "react";

import { displayRoleLabel, type DataScope, type NavItem, type SectionId } from "./navigation";
import type { DemoUser } from "../types";
import type { NotificationItem, NotificationTargetSection } from "../types";
import { NotificationCenter } from "../features/notifications";

interface AppShellProps {
  activeSection: SectionId;
  activeUser: (DemoUser & { is_hr?: boolean }) | null | undefined;
  authError: string | null;
  authMessage: string | null;
  children: ReactNode;
  dataScope: DataScope;
  isLoggingOut: boolean;
  isMarkingAllNotificationsRead: boolean;
  isNotificationsLoading: boolean;
  navItems: NavItem[];
  notifications: NotificationItem[];
  notificationUnreadCount: number;
  onLogout: () => void;
  onMarkAllNotificationsRead: () => void;
  onMarkNotificationRead: (notificationId: number) => void;
  onNotificationNavigate: (section: NotificationTargetSection) => void;
  onSectionChange: (sectionId: SectionId) => void;
}

export function AppShell({
  activeSection,
  activeUser,
  authError,
  authMessage,
  children,
  dataScope,
  isLoggingOut,
  isMarkingAllNotificationsRead,
  isNotificationsLoading,
  navItems,
  notifications,
  notificationUnreadCount,
  onLogout,
  onMarkAllNotificationsRead,
  onMarkNotificationRead,
  onNotificationNavigate,
  onSectionChange,
}: AppShellProps) {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-800">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-5 px-6 py-5">
          <div className="flex items-center gap-4">
            <div className="rounded-xl bg-blue-950 px-3 py-2 font-bold text-white">МГТУ</div>
            <div>
              <h1 className="text-xl font-bold text-slate-950">Профилирование должностей</h1>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <NotificationCenter
              isLoading={isNotificationsLoading}
              isMarkingAll={isMarkingAllNotificationsRead}
              items={notifications}
              onMarkAllRead={onMarkAllNotificationsRead}
              onMarkRead={onMarkNotificationRead}
              onNavigate={onNotificationNavigate}
              unreadCount={notificationUnreadCount}
            />
            <div className="flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-950">
              <span className="font-semibold">
                {activeUser
                  ? `${displayRoleLabel(activeUser)}: ${activeUser.full_name}`
                  : "Проверяю рабочую сессию..."}
              </span>
              <button
                className="rounded-xl bg-white px-3 py-1.5 text-xs font-semibold text-emerald-800 shadow-sm"
                disabled={isLoggingOut}
                onClick={onLogout}
                type="button"
              >
                Выйти
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1600px] px-6 py-7">
        {(authMessage || authError) && (
          <div className="mb-4 rounded-2xl border border-blue-100 bg-white px-5 py-3 text-sm shadow-sm">
            {authMessage && <p className="text-blue-950">{authMessage}</p>}
            {authError && <p className="mt-1 text-red-700">{authError}</p>}
          </div>
        )}
        <section className="mb-6 rounded-2xl border border-blue-100 bg-white p-2 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <p className="px-3 text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
              Рабочая область
            </p>
            <nav className="flex flex-1 flex-wrap gap-2 text-sm">
              {navItems.map((item) => (
                <button
                  className={`rounded-xl px-4 py-2.5 text-left ${
                    activeSection === item.id
                      ? "bg-blue-950 font-semibold text-white shadow-sm"
                      : item.disabled
                        ? "cursor-not-allowed bg-slate-100 text-slate-400"
                        : "bg-slate-50 text-slate-700 hover:bg-blue-50 hover:text-blue-950"
                  }`}
                  disabled={item.disabled}
                  key={item.id}
                  onClick={() => onSectionChange(item.id)}
                  type="button"
                >
                  {item.label}
                  <span
                    className={`ml-2 text-xs font-normal ${
                      activeSection === item.id ? "text-blue-100" : "text-slate-400"
                    }`}
                  >
                    {item.note}
                  </span>
                </button>
              ))}
            </nav>
          </div>
        </section>

        <section className="space-y-6">
          {dataScope === "work" && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-950">
              <p className="font-semibold">Рабочий контур из штатного расписания</p>
              <p className="mt-1 text-amber-800">
                Подразделения и штатные строки загружены в рабочий контур. Сотрудники и руководители
                добавляются HR вручную через структуру; документы сопоставляются отдельно.
              </p>
            </div>
          )}
          {children}
        </section>
      </div>
    </main>
  );
}
