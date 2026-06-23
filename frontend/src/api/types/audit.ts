export interface AuditEvent {
  id: number;
  action: string;
  entity_type: string;
  details: Record<string, unknown>;
  created_at: string | null;
}
