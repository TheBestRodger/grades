import { useQuery } from "@tanstack/react-query";

import { getHrDocuments, getManagerDocuments } from "../../api";
import type { DataScope } from "../../app/navigation";
import { queryKeys } from "../../shared/queryKeys";

export function useDocuments(userId: number | null, dataScope: DataScope, isHr: boolean, isManager: boolean) {
  const documents = useQuery({
    queryKey: queryKeys.hrDocuments(userId, dataScope),
    queryFn: () => getHrDocuments(userId!, dataScope),
    enabled: userId !== null && isHr,
  });
  const managerDocuments = useQuery({
    queryKey: queryKeys.managerDocuments(userId),
    queryFn: () => getManagerDocuments(userId!),
    enabled: userId !== null && isManager,
  });
  return { documents, managerDocuments };
}
