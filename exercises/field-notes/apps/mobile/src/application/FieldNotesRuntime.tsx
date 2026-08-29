// [Implementation 0]
// process/application workspace boundary
export type RuntimeBoundary = { accountId: string; installationId: string };

export function createRuntimeBoundary(): RuntimeBoundary {
  return { accountId: "local-account", installationId: "field-notes-local-installation" };
}
