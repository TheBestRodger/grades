export function formatTimestamp(value: string | null): string {
  if (!value) return "";
  const normalized = value.endsWith("Z") ? value : `${value}Z`;
  return new Date(normalized).toLocaleString("ru-RU");
}
