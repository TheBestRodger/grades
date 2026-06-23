import type { Campaign, OrgNode } from "../../types";
import { selectionState } from "./organizationTreeUtils";

export function CampaignSelectionIndicator({ node, activeCampaign }: { node: OrgNode; activeCampaign: Campaign | null }) {
  const state = selectionState(node, activeCampaign);
  return (
    <span className="grid h-8 w-8 place-items-center rounded-lg border border-current bg-white/70 text-sm font-bold">
      {state.label}
    </span>
  );
}
