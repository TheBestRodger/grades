import { MetricCard } from "./MetricCard";
import { displayFte } from "../shared/formatters";

import type { EmployeeProfile, Summary } from "../types";

export function SummaryMetrics({ summary, profile }: { summary: Summary; profile: EmployeeProfile | null }) {
  if (summary.scope === "self") {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <MetricCard label="Доступ" value="Свой профиль" note="Данные ветки скрыты правилами доступа" />
        <MetricCard
          label="Заполнение анкеты"
          value={profile ? `${Math.round(profile.progress_percent)}%` : "Не назначено"}
          note={profile ? "Сохраненный прогресс в активной кампании" : "Нет участия в активной кампании"}
        />
      </div>
    );
  }

  if (summary.scope === "work") {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Штатные позиции"
          value={String(summary.staffing_lines)}
          note="Загружено в рабочую структуру"
        />
        <MetricCard
          label="Занято по ШР"
          value={displayFte(summary.assigned_fte)}
          note="Колонка «Занято», без персональных данных"
        />
        <MetricCard
          label="Ставки по ШР"
          value={displayFte(summary.approved_fte)}
          note="Сумма поля «Ед. по ШР»"
        />
        <MetricCard
          label="Свободно ставок"
          value={displayFte(summary.vacancy_fte)}
          note="Расчет из ШР: всего минус занято"
        />
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard
        label="Штатные позиции"
        value={String(summary.staffing_lines)}
        note="В доступной ветке"
      />
      <MetricCard
        label="Сотрудники"
        value={String(summary.employees)}
        note="Добавленные назначения"
      />
      <MetricCard
        label="Ставки по ШР"
        value={displayFte(summary.approved_fte)}
        note={`Занято: ${displayFte(summary.assigned_fte)}`}
      />
      <MetricCard
        label="Свободно ставок"
        value={displayFte(summary.vacancy_fte)}
        note="Вакансии являются нормальным состоянием"
      />
    </div>
  );
}
