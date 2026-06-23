import type { Assignment, Campaign, Position } from "../../types";
import { displayFte } from "./organizationTreeUtils";

export function AssignmentRow({
  assignment,
  position,
  activeCampaign,
  canManage,
  canEditStructure,
  changingAssignmentId,
  onEditAssignment,
  onDeleteAssignment,
  onSetAssignment,
}: {
  assignment: Assignment;
  position: Position;
  activeCampaign: Campaign | null;
  canManage: boolean;
  canEditStructure: boolean;
  changingAssignmentId?: number | null;
  onEditAssignment?: (assignment: Assignment, position: Position) => void;
  onDeleteAssignment?: (assignment: Assignment, position: Position) => void;
  onSetAssignment?: (assignmentId: number, included: boolean) => void;
}) {
  const included = new Set(activeCampaign?.participant_assignment_ids ?? []);
  const isIncluded = included.has(assignment.id);
  const className = `rounded-full border px-2.5 py-1 text-xs ${
    isIncluded
      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
      : "border-slate-200 bg-white text-slate-600"
  }`;
  const label = (
    <>
      {isIncluded ? "✓ " : canManage && activeCampaign ? "+ " : ""}
      {assignment.employee_name}
      {position.assigned_fte !== null && ` / ${displayFte(assignment.fte)}`}
    </>
  );

  if (canManage && activeCampaign) {
    return (
      <span className="inline-flex flex-wrap items-center gap-1">
        <button
          aria-label={`${isIncluded ? "Исключить" : "Включить"} назначение ${assignment.employee_name}`}
          className={`${className} hover:border-blue-300 disabled:opacity-50`}
          disabled={changingAssignmentId === assignment.id}
          onClick={() => onSetAssignment?.(assignment.id, !isIncluded)}
          type="button"
        >
          {label}
        </button>
        {canEditStructure && (
          <button
            className="grid h-7 w-7 place-items-center rounded-full border border-blue-200 bg-white text-sm font-bold text-blue-900 hover:bg-blue-50"
            onClick={() => onEditAssignment?.(assignment, position)}
            title="Редактировать карточку сотрудника"
            type="button"
          >
            +
          </button>
        )}
      </span>
    );
  }

  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      <span className={className}>{label}</span>
      {canEditStructure && (
        <button
          className="grid h-7 w-7 place-items-center rounded-full border border-blue-200 bg-white text-sm font-bold text-blue-900 hover:bg-blue-50"
          onClick={() => onEditAssignment?.(assignment, position)}
          title="Редактировать карточку сотрудника"
          type="button"
        >
          +
        </button>
      )}
      {canEditStructure && (
        <button
          className="rounded-full border border-red-200 bg-white px-2.5 py-1 text-xs font-semibold text-red-700 hover:bg-red-50"
          onClick={() => onDeleteAssignment?.(assignment, position)}
          type="button"
        >
          Удалить
        </button>
      )}
    </span>
  );
}
