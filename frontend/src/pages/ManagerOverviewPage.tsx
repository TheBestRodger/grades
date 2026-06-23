import { ManagerOverviewPanel } from "../features/manager";
import type { AppControllerContext } from "../app/types";

interface ManagerOverviewPageProps
  extends Pick<AppControllerContext, "activeSection" | "isManager" | "managerOverview"> {}

export function ManagerOverviewPage({ activeSection, isManager, managerOverview }: ManagerOverviewPageProps) {
  if (!isManager || activeSection !== "manager-overview") return null;

  return (
    <ManagerOverviewPanel
      error={managerOverview.error?.message ?? null}
      isLoading={managerOverview.isLoading}
      overview={managerOverview.data ?? null}
    />
  );
}
