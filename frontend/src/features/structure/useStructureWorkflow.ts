import { useState } from "react";
import type { QueryClient } from "@tanstack/react-query";

import { ApiError } from "../../api";
import type { DataScope } from "../../app/navigation";
import type { EmployeeEditTarget, StructureDeleteTarget } from "../../app/types";
import { invalidateHrViews } from "../../shared/invalidation";
import { queryKeys } from "../../shared/queryKeys";
import type { Assignment, EmployeePasswordResetResult, OrgNode, Position } from "../../types";
import { useStructureMutations } from "./useStructureMutations";

interface UseStructureWorkflowOptions {
  authMe: { refetch: () => Promise<unknown> };
  dataScope: DataScope;
  queryClient: QueryClient;
  selectedUserId: number | null;
  setOperationMessage: (message: string | null) => void;
  setCredentialsFileBlob: (blob: Blob | null) => void;
  setSelectedUserId: (userId: number | null) => void;
}

export function useStructureWorkflow({
  authMe,
  dataScope,
  queryClient,
  selectedUserId,
  setOperationMessage,
  setCredentialsFileBlob,
  setSelectedUserId,
}: UseStructureWorkflowOptions) {
  const [employeeTarget, setEmployeeTarget] = useState<Position | null>(null);
  const [staffingLineTarget, setStaffingLineTarget] = useState<OrgNode | null>(null);
  const [structureDeleteTarget, setStructureDeleteTarget] = useState<StructureDeleteTarget | null>(null);
  const [employeeEditTarget, setEmployeeEditTarget] = useState<EmployeeEditTarget | null>(null);
  const [employeePasswordResetResult, setEmployeePasswordResetResult] =
    useState<EmployeePasswordResetResult | null>(null);

  async function refreshHrViews() {
    await invalidateHrViews(queryClient, selectedUserId, dataScope);
  }

  const {
    addEmployeesMutation,
    updateEmployeeAssignmentMutation,
    resetEmployeePasswordMutation,
    createStaffingLineMutation,
    deleteStructureMutation,
    demoResetMutation,
  } = useStructureMutations({
    selectedUserId,
    dataScope,
    getEmployeeTargetId: () => employeeTarget!.id,
    getEmployeeEditAssignmentId: () => employeeEditTarget!.assignment.id,
    getStaffingLineTargetId: () => staffingLineTarget!.id,
    onAddEmployeesSuccess: async (result) => {
      setOperationMessage(`Добавлено сотрудников: ${result.added.length}. Свободно ставок: ${result.remaining_fte}.`);
      setCredentialsFileBlob(null);
      setEmployeeTarget(null);
      await refreshHrViews();
    },
    onUpdateEmployeeSuccess: async (result) => {
      setOperationMessage(`Карточка сотрудника «${result.full_name}» обновлена.`);
      setEmployeeEditTarget(null);
      setEmployeePasswordResetResult(null);
      await refreshHrViews();
      await authMe.refetch();
    },
    onResetEmployeePasswordSuccess: async (result) => {
      setEmployeePasswordResetResult(result);
      setOperationMessage(`Пароль для «${result.full_name}» перевыпущен.`);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.audit(selectedUserId, dataScope) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.hrReviews(selectedUserId, dataScope) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.managerOverview(null) }),
      ]);
    },
    onCreateStaffingLineSuccess: async (result) => {
      setOperationMessage(`Создана штатная единица «${result.staffing_title}».`);
      setStaffingLineTarget(null);
      await refreshHrViews();
    },
    onDeleteStructureSuccess: async (result) => {
      setOperationMessage(
        `Структура обновлена: удалено назначений ${result.deleted_assignments}, анкет ${result.deleted_profiles}.`,
      );
      setStructureDeleteTarget(null);
      await refreshHrViews();
    },
    onDeleteStructureError: (error, target) => {
      if (error instanceof ApiError && error.status === 409) {
        setStructureDeleteTarget({
          ...target,
          label: structureDeleteTarget?.label ?? "",
          force: true,
          warning: error.message,
        });
      }
    },
    onDemoResetSuccess: async (result) => {
      setOperationMessage(
        result.work_unchanged
          ? "Контур сброшен, рабочие данные сохранены."
          : "Контур сброшен, проверьте рабочий контур.",
      );
      await queryClient.invalidateQueries();
      setSelectedUserId(null);
    },
  });

  function openEmployeeModal(position: Position) {
    addEmployeesMutation.reset();
    setEmployeeTarget(position);
  }

  function openEmployeeEditModal(assignment: Assignment, position: Position) {
    updateEmployeeAssignmentMutation.reset();
    resetEmployeePasswordMutation.reset();
    setEmployeePasswordResetResult(null);
    setEmployeeEditTarget({ assignment, position });
  }

  function openStaffingLineModal(unit: OrgNode) {
    createStaffingLineMutation.reset();
    setStaffingLineTarget(unit);
  }

  function requestDeleteAssignment(assignment: Assignment, position: Position) {
    deleteStructureMutation.reset();
    setStructureDeleteTarget({
      kind: "assignment",
      id: assignment.id,
      label: `${assignment.employee_name} / ${position.title}`,
      force: false,
      warning: null,
    });
  }

  function requestDeletePosition(position: Position) {
    deleteStructureMutation.reset();
    setStructureDeleteTarget({
      kind: "position",
      id: position.id,
      label: position.title,
      force: false,
      warning: null,
    });
  }

  function confirmStructureDelete() {
    if (!structureDeleteTarget) return;
    deleteStructureMutation.mutate(structureDeleteTarget);
  }

  return {
    addEmployeesMutation,
    confirmStructureDelete,
    createStaffingLineMutation,
    deleteStructureMutation,
    demoResetMutation,
    employeeEditTarget,
    employeePasswordResetResult,
    employeeTarget,
    openEmployeeEditModal,
    openEmployeeModal,
    openStaffingLineModal,
    requestDeleteAssignment,
    requestDeletePosition,
    resetEmployeePasswordMutation,
    setEmployeeEditTarget,
    setEmployeePasswordResetResult,
    setEmployeeTarget,
    setStaffingLineTarget,
    setStructureDeleteTarget,
    staffingLineTarget,
    structureDeleteTarget,
    updateEmployeeAssignmentMutation,
  };
}
