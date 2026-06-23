export const auditLabels: Record<string, string> = {
  "campaign.created": "Создана кампания",
  "campaign.wave_created": "Создана волна кампании",
  "campaign.wave_launched": "Волна запущена",
  "campaign.wave_editing_started": "Волна взята в редакцию",
  "campaign.branch_included": "В кампанию включена ветка",
  "campaign.branch_excluded": "Ветка выключена из кампании",
  "document.link_updated": "Обновлена связь документа",
  "employees.work_imported": "Импортированы рабочие сотрудники",
  "staffing_line.work_created": "Создана рабочая штатная строка",
  "employees.bulk_added": "Добавлены сотрудники",
  "campaign.assignments_included": "Включены отдельные назначения",
  "campaign.assignments_excluded": "Выключены отдельные назначения",
  "profile.draft_saved": "Сотрудник сохранил черновик",
  "profile.submitted": "Сотрудник отправил профиль",
  "profile.review_started": "Руководитель взял профиль на проверку",
  "profile.returned_for_revision": "Профиль возвращен на доработку",
  "profile.returned_for_revision_by_hr": "HR вернул профиль сотруднику на доработку",
  "profile.manager_verified": "Профиль подтвержден руководителем",
  "profile.returned_by_hr": "HR вернул профиль руководителю",
  "profile.hr_accepted": "HR принял профиль",
  "profiles.bulk_returned_for_revision": "Руководитель массово вернул профили",
  "profiles.bulk_returned_by_hr": "HR массово вернул профили",
  "demo.reset_completed": "Контур сброшен",
};

export const statusLabels: Record<string, string> = {
  not_started: "Не начали",
  draft: "Черновики",
  submitted: "Сдали",
  under_review: "На проверке",
  returned_for_revision: "На доработке",
  manager_verified: "Ждут HR",
  returned_by_hr: "Возвращены HR",
  hr_accepted: "Приняты HR",
};

export const waveStatusTone: Record<string, string> = {
  draft: "bg-slate-100 text-slate-700",
  active: "bg-emerald-50 text-emerald-800",
  editing: "bg-amber-50 text-amber-800",
};
