import type { EmployeeProfile } from "../../types";

interface ProfileStatusBannersProps {
  latestReturn: EmployeeProfile["review_events"][number] | undefined;
  profile: EmployeeProfile;
}

export function ProfileStatusBanners({ latestReturn, profile }: ProfileStatusBannersProps) {
  return (
    <>
      {profile.workflow_status === "returned_for_revision" && latestReturn?.comment && (
        <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-950">
          <p className="font-semibold">
            {latestReturn.action === "hr_returned"
              ? "HR вернул профиль на доработку"
              : "Руководитель вернул профиль на доработку"}
          </p>
          <p className="mt-2">{latestReturn.comment}</p>
          <p className="mt-2 text-amber-800">
            Исправьте ответы и отправьте новую версию. Предыдущая версия сохранена в истории.
          </p>
        </div>
      )}
      {profile.workflow_status === "under_review" && (
        <div className="mt-5 rounded-2xl border border-indigo-200 bg-indigo-50 px-5 py-4 text-sm text-indigo-950">
          <p className="font-semibold">Профиль находится на проверке руководителя</p>
          <p className="mt-1">Редактирование временно заблокировано до решения руководителя.</p>
        </div>
      )}
      {profile.workflow_status === "manager_verified" && (
        <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-950">
          <p className="font-semibold">Профиль подтвержден руководителем</p>
          <p className="mt-1">Версия зафиксирована и ожидает следующего этапа обработки HR.</p>
        </div>
      )}
      {profile.workflow_status === "returned_by_hr" && (
        <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-950">
          <p className="font-semibold">HR вернул профиль вашему руководителю</p>
          <p className="mt-1">
            Редактирование пока закрыто. Руководитель решит, нужна ли новая доработка с вашей стороны.
          </p>
        </div>
      )}
      {profile.workflow_status === "hr_accepted" && (
        <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-950">
          <p className="font-semibold">Профиль принят HR</p>
          <p className="mt-1">Профиль завершен в рамках текущей кампании и сохранен в истории.</p>
        </div>
      )}
    </>
  );
}
