import { useQuery } from "@tanstack/react-query";

import { getHrProfileReviews } from "../../api";
import type { DataScope } from "../../app/navigation";
import { queryKeys } from "../../shared/queryKeys";

export function useHrReviews(userId: number | null, dataScope: DataScope, enabled: boolean) {
  const hrReviews = useQuery({
    queryKey: queryKeys.hrReviews(userId, dataScope),
    queryFn: () => getHrProfileReviews(userId!, dataScope),
    enabled: userId !== null && enabled,
  });
  return { hrReviews };
}
