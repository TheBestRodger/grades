import { HrAnalyticsPanel } from "../features/analytics";
import type { AppControllerContext } from "../app/types";

interface AnalyticsPageProps
  extends Pick<AppControllerContext, "activeSection" | "dataScope" | "hrAnalytics" | "isHr"> {}

export function AnalyticsPage({ activeSection, dataScope, hrAnalytics, isHr }: AnalyticsPageProps) {
  if (!isHr || activeSection !== "analytics") return null;
  if (dataScope !== "work" && dataScope !== "demo") return null;

  return (
    <HrAnalyticsPanel
      analytics={hrAnalytics.data ?? null}
      error={hrAnalytics.error?.message ?? null}
      isLoading={hrAnalytics.isLoading}
    />
  );
}
