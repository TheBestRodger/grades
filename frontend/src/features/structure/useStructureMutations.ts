import { useMutation } from "@tanstack/react-query";

import {
  bulkAddEmployees,
  createWorkStaffingLine,
  deleteWorkAssignment,
  deleteWorkStaffingLine,
  resetDemoData,
  resetEmployeePassword,
  updateEmployeeAssignment,
} from "../../api";
import type { DataScope } from "../../app/navigation";
import type {
  BulkEmployeeResult,
  DemoResetResult,
  EmployeeAssignmentUpdate,
  EmployeePasswordResetResult,
  NewEmployee,
  StructureDeleteResult,
  WorkStaffingLineInput,
  WorkStaffingLineResult,
} from "../../types";

interface StructureDeleteTargetInput {
  kind: "assignment" | "position";
  id: number;
  force: boolean;
}

interface StructureMutationOptions {
  selectedUserId: number | null;
  dataScope: DataScope;
  getEmployeeTargetId: () => number;
  getEmployeeEditAssignmentId: () => number;
  getStaffingLineTargetId: () => number;
  onAddEmployeesSuccess?: (result: BulkEmployeeResult) => void | Promise<void>;
  onUpdateEmployeeSuccess?: (result: { full_name: string }) => void | Promise<void>;
  onResetEmployeePasswordSuccess?: (result: EmployeePasswordResetResult) => void | Promise<void>;
  onCreateStaffingLineSuccess?: (result: WorkStaffingLineResult) => void | Promise<void>;
  onDeleteStructureSuccess?: (result: StructureDeleteResult) => void | Promise<void>;
  onDeleteStructureError?: (error: unknown, target: StructureDeleteTargetInput) => void;
  onDemoResetSuccess?: (result: DemoResetResult) => void | Promise<void>;
}

export function useStructureMutations(options: StructureMutationOptions) {
  const addEmployeesMutation = useMutation({
    mutationFn: (rows: NewEmployee[]) =>
      bulkAddEmployees(options.selectedUserId!, options.getEmployeeTargetId(), rows, options.dataScope),
    onSuccess: options.onAddEmployeesSuccess,
  });
  const updateEmployeeAssignmentMutation = useMutation({
    mutationFn: (payload: EmployeeAssignmentUpdate) =>
      updateEmployeeAssignment(
        options.selectedUserId!,
        options.getEmployeeEditAssignmentId(),
        payload,
        options.dataScope,
      ),
    onSuccess: options.onUpdateEmployeeSuccess,
  });
  const resetEmployeePasswordMutation = useMutation({
    mutationFn: () =>
      resetEmployeePassword(
        options.selectedUserId!,
        options.getEmployeeEditAssignmentId(),
        options.dataScope,
      ),
    onSuccess: options.onResetEmployeePasswordSuccess,
  });
  const createStaffingLineMutation = useMutation({
    mutationFn: (payload: WorkStaffingLineInput) =>
      createWorkStaffingLine(options.selectedUserId!, options.getStaffingLineTargetId(), payload),
    onSuccess: options.onCreateStaffingLineSuccess,
  });
  const deleteStructureMutation = useMutation({
    mutationFn: (target: StructureDeleteTargetInput) =>
      target.kind === "assignment"
        ? deleteWorkAssignment(options.selectedUserId!, target.id, target.force)
        : deleteWorkStaffingLine(options.selectedUserId!, target.id, target.force),
    onSuccess: options.onDeleteStructureSuccess,
    onError: options.onDeleteStructureError,
  });
  const demoResetMutation = useMutation({
    mutationFn: () => resetDemoData(options.selectedUserId!),
    onSuccess: options.onDemoResetSuccess,
  });

  return {
    addEmployeesMutation,
    updateEmployeeAssignmentMutation,
    resetEmployeePasswordMutation,
    createStaffingLineMutation,
    deleteStructureMutation,
    demoResetMutation,
  };
}
