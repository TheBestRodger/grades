import type { AiUsage, LocalDraftPayload } from "./types";

export function localDraftStorageKey(profileId: number): string {
  return `grades-profile-draft-v2:${profileId}`;
}

export function loadLocalDraft(profileId: number): LocalDraftPayload | null {
  const raw = window.localStorage.getItem(localDraftStorageKey(profileId));
  if (!raw) return null;
  return JSON.parse(raw) as LocalDraftPayload;
}

export function saveLocalDraft(
  profileId: number,
  answers: Record<string, string>,
  aiUsage: AiUsage,
): void {
  window.localStorage.setItem(
    localDraftStorageKey(profileId),
    JSON.stringify({ answers, ai_usage: aiUsage, updated_at: new Date().toISOString() }),
  );
}

export function removeLocalDraft(profileId: number): void {
  window.localStorage.removeItem(localDraftStorageKey(profileId));
}
