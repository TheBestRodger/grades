export function displayFte(value: number | null): string {
  return value === null ? "-" : value.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
}
