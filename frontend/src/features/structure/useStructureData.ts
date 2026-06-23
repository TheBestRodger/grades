import { useQuery } from "@tanstack/react-query";

import { getManagerOptions, getSummary, getTree, getWorkSummary, getWorkTree } from "../../api";
import type { DataScope } from "../../app/navigation";
import { queryKeys } from "../../shared/queryKeys";

export function useStructureData(userId: number | null, isHr: boolean, dataScope: DataScope) {
  const summary = useQuery({
    queryKey: queryKeys.summary(userId),
    queryFn: () => getSummary(userId!),
    enabled: userId !== null,
  });
  const tree = useQuery({
    queryKey: queryKeys.tree(userId),
    queryFn: () => getTree(userId!),
    enabled: userId !== null,
  });
  const workTree = useQuery({
    queryKey: queryKeys.workTree(userId),
    queryFn: () => getWorkTree(userId!),
    enabled: userId !== null && (isHr || dataScope === "work"),
  });
  const workSummary = useQuery({
    queryKey: queryKeys.workSummary(userId),
    queryFn: () => getWorkSummary(userId!),
    enabled: userId !== null && (isHr || dataScope === "work"),
  });
  const managers = useQuery({
    queryKey: queryKeys.managers(userId),
    queryFn: () => getManagerOptions(userId!),
    enabled: userId !== null && isHr,
  });
  const workManagers = useQuery({
    queryKey: queryKeys.workManagers(userId),
    queryFn: () => getManagerOptions(userId!, "work"),
    enabled: userId !== null && isHr,
  });

  return { summary, tree, workTree, workSummary, managers, workManagers };
}
