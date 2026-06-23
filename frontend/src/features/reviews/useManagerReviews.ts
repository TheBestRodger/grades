import { useQuery } from "@tanstack/react-query";

import { getManagerOverview, getManagerReviews } from "../../api";
import { queryKeys } from "../../shared/queryKeys";

export function useManagerReviews(userId: number | null, enabled: boolean) {
  const managerReviews = useQuery({
    queryKey: queryKeys.managerReviews(userId),
    queryFn: () => getManagerReviews(userId!),
    enabled: userId !== null && enabled,
  });
  const managerOverview = useQuery({
    queryKey: queryKeys.managerOverview(userId),
    queryFn: () => getManagerOverview(userId!),
    enabled: userId !== null && enabled,
  });
  return { managerReviews, managerOverview };
}
