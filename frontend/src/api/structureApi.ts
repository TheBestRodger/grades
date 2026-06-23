import { authHeaders, readResponseError, request } from "./request";
import { API_URL } from "./urls";
import type {
  BulkEmployeeResult,
  EmployeeAssignmentUpdate,
  EmployeeAssignmentUpdateResult,
  EmployeePasswordResetResult,
  NewEmployee,
  StructureDeleteResult,
  WorkEmployeeImportResult,
  WorkStaffingLineInput,
  WorkStaffingLineResult,
} from "./types";

export const bulkAddEmployees = (
  userId: number,
  staffingLineId: number,
  employees: NewEmployee[],
  scope: "demo" | "work" = "demo",
) =>
  request<BulkEmployeeResult>(API_URL.structure.staffingLineEmployeesBulk(scope, staffingLineId), {
    userId,
    method: "POST",
    body: { employees },
  });

export const updateEmployeeAssignment = (
  userId: number,
  assignmentId: number,
  payload: EmployeeAssignmentUpdate,
  scope: "demo" | "work" = "demo",
) =>
  request<EmployeeAssignmentUpdateResult>(API_URL.structure.assignmentEmployee(scope, assignmentId), {
    userId,
    method: "PUT",
    body: payload,
  });

export const resetEmployeePassword = (userId: number, assignmentId: number, scope: "demo" | "work" = "demo") =>
  request<EmployeePasswordResetResult>(API_URL.structure.assignmentPasswordReset(scope, assignmentId), {
    userId,
    method: "POST",
  });

export const importWorkEmployees = async (_userId: number, file: File) => {
  const response = await fetch(API_URL.structure.importWorkEmployees(file.name), {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/octet-stream",
    },
    body: file,
  });
  if (!response.ok) {
    throw new Error(await readResponseError(response));
  }
  return (await response.json()) as WorkEmployeeImportResult;
};

export const createWorkStaffingLine = (userId: number, orgUnitId: number, payload: WorkStaffingLineInput) =>
  request<WorkStaffingLineResult>(API_URL.structure.createWorkStaffingLine(orgUnitId), {
    userId,
    method: "POST",
    body: payload,
  });

export const deleteWorkAssignment = (userId: number, assignmentId: number, force = false) =>
  request<StructureDeleteResult>(API_URL.structure.deleteWorkAssignment(assignmentId, force), {
    userId,
    method: "DELETE",
  });

export const deleteWorkStaffingLine = (userId: number, staffingLineId: number, force = false) =>
  request<StructureDeleteResult>(API_URL.structure.deleteWorkStaffingLine(staffingLineId, force), {
    userId,
    method: "DELETE",
  });
