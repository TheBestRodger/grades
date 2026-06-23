import type { AiConfiguration } from "./settings";

export interface AiStatus {
  mode: string;
  provider: string;
  available: boolean;
  label: string;
  fallback_message: string;
  configuration?: AiConfiguration;
}

export interface Health {
  status: string;
  environment: string;
  ai: AiStatus;
}
