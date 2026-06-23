import { authHeaders, readResponseError } from "./request";
import { API_URL } from "./urls";
import type { CredentialsExportRow, HrExportFormat, HrExportKind } from "./types";

function saveBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export const downloadHrExport = async (_userId: number, kind: HrExportKind, format: HrExportFormat) => {
  const response = await fetch(API_URL.exports.hr(kind, format), {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await readResponseError(response));
  }
  saveBlob(await response.blob(), `${kind}_export.${format}`);
};

export const downloadCredentialsExport = async (rows: CredentialsExportRow[]) => {
  const response = await fetch(API_URL.exports.credentials, {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ rows }),
  });
  if (!response.ok) {
    throw new Error(await readResponseError(response));
  }
  saveBlob(await response.blob(), "credentials.xlsx");
};

export const issueWaveCredentialsExport = async (
  _userId: number,
  scope: "demo" | "work",
  campaignId: number,
  waveId: number,
): Promise<Blob> => {
  const response = await fetch(API_URL.campaigns.waveCredentials(scope, campaignId, waveId), {
    method: "POST",
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await readResponseError(response));
  }
  return response.blob();
};

export const downloadProfileTemplateExport = async (_userId: number, profileId: number) => {
  const response = await fetch(API_URL.exports.profileTemplate(profileId), {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await readResponseError(response));
  }
  saveBlob(await response.blob(), `profile_${profileId}_template.xlsx`);
};
