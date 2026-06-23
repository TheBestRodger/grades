import { useQuery } from "@tanstack/react-query";

import { getCampaigns, getRecentAudit } from "../../api";
import type { DataScope } from "../../app/navigation";
import { queryKeys } from "../../shared/queryKeys";

export function useCampaigns(userId: number | null, dataScope: DataScope, enabled: boolean) {
  const campaigns = useQuery({
    queryKey: queryKeys.campaigns(userId, dataScope),
    queryFn: () => getCampaigns(userId!, dataScope),
    enabled: userId !== null && enabled,
  });
  const audit = useQuery({
    queryKey: queryKeys.audit(userId, dataScope),
    queryFn: () => getRecentAudit(userId!, dataScope),
    enabled: userId !== null && enabled,
  });
  return { campaigns, audit };
}
