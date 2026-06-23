export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function normalizeErrorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const record = item as Record<string, unknown>;
          if (typeof record.msg === "string") return record.msg;
          if (typeof record.detail === "string") return record.detail;
        }
        return String(item);
      })
      .filter(Boolean);
    if (parts.length > 0) return parts.join("; ");
  }
  if (detail && typeof detail === "object") {
    const record = detail as Record<string, unknown>;
    if (typeof record.detail === "string") return record.detail;
    if (Array.isArray(record.detail)) return normalizeErrorDetail(record.detail);
    if (typeof record.message === "string") return record.message;
    return JSON.stringify(detail);
  }
  if (detail === null || detail === undefined) return "";
  return String(detail);
}

function storedAuthToken(): string | null {
  return window.localStorage.getItem("auth_token");
}

export function authHeaders(): Record<string, string> {
  const token = storedAuthToken();
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function readResponseError(response: Response): Promise<string> {
  const payload = (await response.json().catch(() => null)) as { detail?: unknown } | null;
  return normalizeErrorDetail(payload?.detail) || `Request failed: ${response.status}`;
}

export async function request<T>(
  url: string,
  options: { userId?: number; method?: "DELETE" | "GET" | "POST" | "PUT"; body?: unknown } = {},
): Promise<T> {
  const response = await fetch(url, {
    method: options.method ?? "GET",
    headers: {
      ...authHeaders(),
      ...(options.body ? { "Content-Type": "application/json" } : {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    throw new ApiError(await readResponseError(response), response.status);
  }
  return (await response.json()) as T;
}
