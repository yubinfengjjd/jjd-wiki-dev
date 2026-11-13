import { PageSummary, Workflow } from './api';

/** Queue owner comes from the shared backend derivation, never raw status counts. */
export function queueOf(page: PageSummary): Workflow['queue'] {
  return page.workflow?.queue ?? null;
}

export function pendingCount(pages: PageSummary[]): number {
  return pages.filter((p) => queueOf(p) !== null).length;
}
