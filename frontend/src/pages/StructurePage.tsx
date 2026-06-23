import { SummaryMetrics } from "../components/SummaryMetrics";
import { DemoResetPanel } from "../features/structure";
import { OrganizationTreePanel } from "../features/organization";
import { displayRoleLabel } from "../app/navigation";
import type { AppControllerContext } from "../app/types";
import type { DemoResetResult } from "../types";

interface StructurePageProps
  extends Pick<
    AppControllerContext,
    | "activeCampaignForTree"
    | "activePersonalProfile"
    | "activeSection"
    | "activeUser"
    | "changingAssignmentId"
    | "dataScope"
    | "excludingUnitId"
    | "includingUnitId"
    | "isHr"
    | "selectedUser"
    | "summary"
    | "tree"
    | "workSummary"
    | "workTree"
  > {
  demoResetError: string | null;
  demoResetResult: DemoResetResult | null;
  isDemoResetting: boolean;
  onAddEmployee: AppControllerContext["openEmployeeModal"];
  onCreatePosition: AppControllerContext["openStaffingLineModal"];
  onDeleteAssignment: AppControllerContext["requestDeleteAssignment"];
  onDeletePosition: AppControllerContext["requestDeletePosition"];
  onEditAssignment: AppControllerContext["openEmployeeEditModal"];
  onExcludeUnit: AppControllerContext["excludeUnit"];
  onIncludeUnit: AppControllerContext["includeUnit"];
  onResetDemo: () => void;
  onSetAssignment: AppControllerContext["setAssignmentParticipation"];
}

export function StructurePage({
  activeCampaignForTree,
  activePersonalProfile,
  activeSection,
  activeUser,
  changingAssignmentId,
  dataScope,
  demoResetError,
  demoResetResult,
  isDemoResetting,
  isHr,
  onAddEmployee,
  onCreatePosition,
  onDeleteAssignment,
  onDeletePosition,
  onEditAssignment,
  onExcludeUnit,
  onIncludeUnit,
  onResetDemo,
  onSetAssignment,
  selectedUser,
  summary,
  tree,
  workSummary,
  workTree,
  excludingUnitId,
  includingUnitId,
}: StructurePageProps) {
  if (activeSection !== "structure") return null;

  if (dataScope === "work" && isHr) {
    return (
      <>
        {workSummary.data && <SummaryMetrics profile={null} summary={workSummary.data} />}
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
              Рабочая структура
            </p>
            <h2 className="mt-1 text-2xl font-bold text-slate-950">
              ШР по уровням на 15.05.2026
            </h2>
          </div>
          <p className="rounded-full bg-slate-200 px-4 py-2 text-sm font-medium text-slate-700">
            {workSummary.data?.employees
              ? `Загружено сотрудников: ${workSummary.data.employees}`
              : "Персональные данные не загружены"}
          </p>
        </div>
        {workTree.isLoading && <p className="text-slate-500">Загружаю рабочую структуру...</p>}
        {workTree.error && <p className="text-red-700">Не удалось загрузить рабочую структуру.</p>}
        {workTree.data && (
          <OrganizationTreePanel
            activeCampaign={null}
            canAddEmployees
            canEditStructure
            canManage={false}
            excludingUnitId={null}
            includingUnitId={null}
            nodes={workTree.data.nodes}
            onAdd={onAddEmployee}
            onCreatePosition={onCreatePosition}
            onEditAssignment={onEditAssignment}
            onDeleteAssignment={onDeleteAssignment}
            onDeletePosition={onDeletePosition}
            onExclude={onExcludeUnit}
            onInclude={onIncludeUnit}
            onSetAssignment={onSetAssignment}
          />
        )}
      </>
    );
  }

  if (dataScope === "demo" && (selectedUser?.role !== "employee" || isHr)) {
    return (
      <>
        {isHr && (
          <DemoResetPanel
            error={demoResetError}
            isResetting={isDemoResetting}
            onReset={onResetDemo}
            result={demoResetResult}
          />
        )}
        {summary.data && <SummaryMetrics profile={activePersonalProfile} summary={summary.data} />}
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
              Видимость роли
            </p>
            <h2 className="mt-1 text-2xl font-bold text-slate-950">
              {displayRoleLabel(selectedUser)}: {selectedUser?.full_name}
            </h2>
          </div>
          <p className="rounded-full bg-blue-100 px-4 py-2 text-sm font-medium text-blue-900">
            Структура в разрешённой зоне
          </p>
        </div>
        {tree.isLoading && <p className="text-slate-500">Загружаю структуру...</p>}
        {tree.error && <p className="text-red-700">Не удалось загрузить структуру.</p>}
        {tree.data && (
          <OrganizationTreePanel
            activeCampaign={activeCampaignForTree}
            canEditStructure={Boolean(isHr)}
            canManage={Boolean(isHr)}
            changingAssignmentId={changingAssignmentId}
            excludingUnitId={excludingUnitId}
            includingUnitId={includingUnitId}
            nodes={tree.data.nodes}
            onAdd={onAddEmployee}
            onEditAssignment={onEditAssignment}
            onExclude={onExcludeUnit}
            onInclude={onIncludeUnit}
            onSetAssignment={onSetAssignment}
          />
        )}
      </>
    );
  }

  if (dataScope === "work" && !isHr && activeUser?.role !== "employee") {
    return (
      <>
        {workSummary.data && <SummaryMetrics profile={activePersonalProfile} summary={workSummary.data} />}
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
              Видимость роли
            </p>
            <h2 className="mt-1 text-2xl font-bold text-slate-950">
              {displayRoleLabel(activeUser)}: {activeUser?.full_name}
            </h2>
          </div>
          <p className="rounded-full bg-blue-100 px-4 py-2 text-sm font-medium text-blue-900">
            Структура в разрешённой зоне
          </p>
        </div>
        {workTree.isLoading && <p className="text-slate-500">Загружаю структуру...</p>}
        {workTree.error && <p className="text-red-700">Не удалось загрузить структуру.</p>}
        {workTree.data && (
          <OrganizationTreePanel
            activeCampaign={null}
            canManage={false}
            excludingUnitId={null}
            includingUnitId={null}
            nodes={workTree.data.nodes}
            onAdd={onAddEmployee}
            onExclude={onExcludeUnit}
            onInclude={onIncludeUnit}
            onSetAssignment={onSetAssignment}
          />
        )}
      </>
    );
  }

  return null;
}
