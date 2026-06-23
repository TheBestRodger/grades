import type { Assignment, Campaign, Position } from "../../types";
import { AssignmentRow } from "./AssignmentRow";
import { displayFte } from "./organizationTreeUtils";

export function StaffingLineRow({
  position,
  canAddEmployees,
  canManage,
  canEditStructure,
  activeCampaign,
  changingAssignmentId,
  onAdd,
  onEditAssignment,
  onDeleteAssignment,
  onDeletePosition,
  onSetAssignment,
}: {
  position: Position;
  canAddEmployees: boolean;
  canManage: boolean;
  canEditStructure: boolean;
  activeCampaign: Campaign | null;
  changingAssignmentId?: number | null;
  onAdd: (position: Position) => void;
  onEditAssignment?: (assignment: Assignment, position: Position) => void;
  onDeleteAssignment?: (assignment: Assignment, position: Position) => void;
  onDeletePosition?: (position: Position) => void;
  onSetAssignment?: (assignmentId: number, included: boolean) => void;
}) {
  const canOpenEmployeeModal = canAddEmployees && (position.vacancy_fte ?? 0) > 0;
  return (
    <div className="ml-8 border-l border-slate-100 pl-4">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-slate-50 px-3 py-2">
        <div>
          <p className="text-sm font-semibold text-slate-900">{position.title}</p>
          {position.approved_fte !== null && (
            <p className="text-xs text-slate-500">
              ШР {displayFte(position.approved_fte)} / занято {displayFte(position.assigned_fte)} / свободно{" "}
              {displayFte(position.vacancy_fte)}
            </p>
          )}
        </div>
        {(canOpenEmployeeModal || canEditStructure) && (
          <div className="flex flex-wrap gap-2">
            {canOpenEmployeeModal && (
              <button
                className="rounded-full bg-blue-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800"
                onClick={() => onAdd(position)}
                type="button"
              >
                Добавить людей
              </button>
            )}
            {canEditStructure && (
              <button
                className="rounded-full border border-red-200 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50"
                onClick={() => onDeletePosition?.(position)}
                type="button"
              >
                Удалить штатную единицу
              </button>
            )}
          </div>
        )}
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {position.assignments.map((assignment) => (
          <AssignmentRow
            activeCampaign={activeCampaign}
            assignment={assignment}
            canEditStructure={canEditStructure}
            canManage={canManage}
            changingAssignmentId={changingAssignmentId}
            key={assignment.id}
            onDeleteAssignment={onDeleteAssignment}
            onEditAssignment={onEditAssignment}
            onSetAssignment={onSetAssignment}
            position={position}
          />
        ))}
      </div>
    </div>
  );
}
