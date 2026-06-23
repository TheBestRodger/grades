import type { AuditEvent } from "../../types";
import { auditLabels } from "./campaignConstants";
import { formatTimestamp } from "./campaignFormatters";

export function AuditPanel({ events }: { events: AuditEvent[] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Аудит действий</p>
      <h3 className="mt-2 text-lg font-bold text-slate-950">Последние операции процесса</h3>
      <div className="mt-4 space-y-3">
        {events.length === 0 && <p className="text-sm text-slate-500">Операций пока нет.</p>}
        {events.slice(0, 5).map((event) => (
          <div className="rounded-xl bg-slate-50 px-3 py-2 text-sm" key={event.id}>
            <p className="font-medium text-slate-800">{auditLabels[event.action] ?? event.action}</p>
            <p className="text-xs text-slate-500">{formatTimestamp(event.created_at)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
