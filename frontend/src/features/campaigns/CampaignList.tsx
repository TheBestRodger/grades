import type { Campaign } from "../../types";

export function CampaignList({
  campaigns,
  activeCampaignId,
  isWork,
  onActiveChange,
}: {
  campaigns: Campaign[];
  activeCampaignId: number | null;
  isWork: boolean;
  onActiveChange: (id: number) => void;
}) {
  if (campaigns.length === 0) return null;

  return (
    <div className="mt-5 border-t border-slate-100 pt-4">
      <label className="text-sm font-medium text-slate-700">
        Активная кампания
        <select
          className="mt-2 block w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
          onChange={(event) => onActiveChange(Number(event.target.value))}
          value={activeCampaignId ?? ""}
        >
          {campaigns.map((campaign) => (
            <option key={campaign.id} value={campaign.id}>
              {campaign.name} / {isWork
                ? `участников: ${campaign.participants_expected}, подразделений: ${campaign.selected_units_count}`
                : `всего ожидаем: ${campaign.total_participants_expected}`}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
