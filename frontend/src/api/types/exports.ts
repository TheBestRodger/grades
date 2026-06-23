export type HrExportKind = "profiles" | "campaigns";
export type HrExportFormat = "csv" | "json";

export interface CredentialsExportRow {
  full_name: string;
  email: string;
  username: string;
  password: string;
  role?: string;
  position?: string;
}
