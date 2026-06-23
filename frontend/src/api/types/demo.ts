export interface DemoResetResult {
  scope: "demo";
  before: Record<"demo" | "work", Record<string, number>>;
  after: Record<"demo" | "work", Record<string, number>>;
  work_unchanged: boolean;
}
