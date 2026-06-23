import type { DemoUser } from "../types";

export type SectionId =
  | "profile"
  | "structure"
  | "campaigns"
  | "manager-overview"
  | "manager-reviews"
  | "hr-reviews"
  | "documents"
  | "analytics"
  | "settings"
  | "export";

export type DataScope = "demo" | "work";

export interface NavItem {
  id: SectionId;
  label: string;
  note: string;
  disabled?: boolean;
}

export const roleLabels: Record<DemoUser["role"], string> = {
  hr: "HR",
  manager: "Руководитель",
  employee: "Сотрудник",
};

export function displayRoleLabel(user?: { role: DemoUser["role"]; is_hr?: boolean } | null): string {
  if (!user) return "Загрузка";
  return `${roleLabels[user.role]}${user.is_hr && user.role !== "hr" ? " + HR" : ""}`;
}

export function navForRole(role?: DemoUser["role"], hasHrAccess = false): NavItem[] {
  if (!role) return [];
  const items: NavItem[] = [];
  const add = (item: NavItem) => {
    if (!items.some((existing) => existing.id === item.id)) {
      items.push(item);
    }
  };

  if (role === "employee") {
    add({ id: "profile", label: "Моя анкета", note: "статус и заполнение" });
  }

  if (role === "manager") {
    add({ id: "profile", label: "Моя анкета", note: "свой профиль" });
    add({ id: "manager-overview", label: "Анализ", note: "heat map и drill-down" });
    add({ id: "manager-reviews", label: "Проверка", note: "профили подчиненных" });
    add({ id: "documents", label: "Документы", note: "моя зона" });
    add({ id: "structure", label: "Структура", note: "моя ветка" });
  }

  if (role === "hr" || hasHrAccess) {
    add({ id: "structure", label: "Структура", note: "сотрудники и ставки" });
    add({ id: "campaigns", label: "Кампании", note: "включение веток" });
    add({ id: "hr-reviews", label: "Финальная проверка", note: "решения HR" });
    add({ id: "documents", label: "Документы", note: "ДИ и покрытия" });
    add({ id: "analytics", label: "Аналитика", note: "KPI и воронка" });
    // add({ id: "settings", label: "Настройки", note: "ИИ и анкета" });
    add({ id: "profile", label: "Моя анкета", note: "свой профиль" });
  }

  return items;
}
