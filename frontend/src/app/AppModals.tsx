import { StructureDeleteConfirm } from "../components/StructureDeleteConfirm";
import { EmployeeEditModal, EmployeeModal, StaffingLineModal } from "../features/structure";
import type { AppControllerContext } from "./types";

interface AppModalsProps {
  context: AppControllerContext;
}

export function AppModals({ context }: AppModalsProps) {
  const {
    addEmployeesMutation,
    createStaffingLineMutation,
    dataScope,
    deleteStructureMutation,
    employeeEditTarget,
    employeePasswordResetResult,
    employeeTarget,
    isHr,
    managers,
    resetEmployeePasswordMutation,
    setEmployeeEditTarget,
    setEmployeePasswordResetResult,
    setEmployeeTarget,
    setStaffingLineTarget,
    setStructureDeleteTarget,
    staffingLineTarget,
    structureDeleteTarget,
    updateEmployeeAssignmentMutation,
    workManagers,
    confirmStructureDelete,
  } = context;

  if (!isHr) return null;

  return (
    <>
      <EmployeeModal
        allowRoleSelection
        error={addEmployeesMutation.error?.message ?? null}
        isSaving={addEmployeesMutation.isPending}
        managers={dataScope === "work" ? workManagers.data ?? [] : managers.data ?? []}
        onClose={() => setEmployeeTarget(null)}
        onSave={(rows) => addEmployeesMutation.mutate(rows)}
        target={employeeTarget}
      />

      <EmployeeEditModal
        assignment={employeeEditTarget?.assignment ?? null}
        error={updateEmployeeAssignmentMutation.error?.message ?? null}
        isSaving={updateEmployeeAssignmentMutation.isPending}
        isResettingPassword={resetEmployeePasswordMutation.isPending}
        passwordResetError={resetEmployeePasswordMutation.error?.message ?? null}
        passwordResetResult={employeePasswordResetResult}
        onClose={() => {
          setEmployeeEditTarget(null);
          setEmployeePasswordResetResult(null);
        }}
        onResetPassword={() => resetEmployeePasswordMutation.mutateAsync()}
        onSave={(payload) => updateEmployeeAssignmentMutation.mutate(payload)}
      />

      <StaffingLineModal
        error={createStaffingLineMutation.error?.message ?? null}
        isSaving={createStaffingLineMutation.isPending}
        onClose={() => setStaffingLineTarget(null)}
        onSave={(payload) => createStaffingLineMutation.mutate(payload)}
        target={staffingLineTarget}
      />

      <StructureDeleteConfirm
        error={
          structureDeleteTarget?.warning
            ? null
            : deleteStructureMutation.error instanceof Error
              ? deleteStructureMutation.error.message
              : null
        }
        isDeleting={deleteStructureMutation.isPending}
        onCancel={() => setStructureDeleteTarget(null)}
        onConfirm={confirmStructureDelete}
        target={structureDeleteTarget}
      />
    </>
  );
}
