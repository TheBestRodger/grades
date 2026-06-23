import { useQuery } from "@tanstack/react-query";

import { getHealth, getMyProfiles } from "../../api";
import { queryKeys } from "../../shared/queryKeys";

export function useMyProfiles(userId: number | null) {
  const health = useQuery({ queryKey: queryKeys.health(), queryFn: getHealth });
  const personalProfiles = useQuery({
    queryKey: queryKeys.myProfiles(userId),
    queryFn: () => getMyProfiles(userId!),
    enabled: userId !== null,
  });
  return { health, personalProfiles };
}
