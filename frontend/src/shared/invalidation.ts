import type { QueryClient } from "@tanstack/react-query";
import type { DataScope } from "../app/navigation";
import { queryKeys } from "./queryKeys";

export async function invalidateHrViews(
  queryClient: QueryClient,
  userId: number | null,
  _scope: DataScope,
) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: queryKeys.tree(userId) }),
    queryClient.invalidateQueries({ queryKey: queryKeys.summary(userId) }),
    queryClient.invalidateQueries({ queryKey: queryKeys.demoUsers() }),
    queryClient.invalidateQueries({ queryKey: queryKeys.campaigns(userId) }),
    queryClient.invalidateQueries({ queryKey: queryKeys.audit(userId) }),
    queryClient.invalidateQueries({ queryKey: queryKeys.hrAnalytics(userId) }),
    queryClient.invalidateQueries({ queryKey: queryKeys.hrReviews(userId) }),
    queryClient.invalidateQueries({ queryKey: ["manager-overview"] }),
    queryClient.invalidateQueries({ queryKey: queryKeys.workTree(userId) }),
    queryClient.invalidateQueries({ queryKey: queryKeys.workSummary(userId) }),
    queryClient.invalidateQueries({ queryKey: queryKeys.managers(userId) }),
    queryClient.invalidateQueries({ queryKey: queryKeys.workManagers(userId) }),
  ]);
}

export async function invalidateQuestionnaireViews(queryClient: QueryClient) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["my-profiles"] }),
    queryClient.invalidateQueries({ queryKey: ["manager-reviews"] }),
    queryClient.invalidateQueries({ queryKey: ["hr-profile-reviews"] }),
    queryClient.invalidateQueries({ queryKey: ["audit"] }),
  ]);
}
