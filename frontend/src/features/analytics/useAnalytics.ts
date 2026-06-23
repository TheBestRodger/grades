import { useQuery } from "@tanstack/react-query";

import { getHrAnalytics } from "../../api";
import type { DataScope } from "../../app/navigation";
import { queryKeys } from "../../shared/queryKeys";

export function useAnalytics(userId: number | null, dataScope: DataScope, enabled: boolean) {
  const hrAnalytics = useQuery({
    queryKey: queryKeys.hrAnalytics(userId, dataScope),
    queryFn: () => getHrAnalytics(userId!, dataScope),
    enabled: userId !== null && enabled,
  });
  return { hrAnalytics };
}
