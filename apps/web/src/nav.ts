import type { MouseEvent } from 'react';
import { api, pageHref } from './api';

const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

/**
 * Open a page. The page is fetched first so the new view can paint immediately; the
 * element passed as `from` morphs into the page's figure plate (View Transitions).
 */
export async function openPage(path: string, from?: HTMLElement) {
  // A failed prefetch still navigates; the page view shows the error instead of a dead click.
  await api.page(path).catch(() => undefined);
  const go = () => {
    location.hash = pageHref(path);
  };
  if (!document.startViewTransition || reduced()) return go();
  if (from) from.style.viewTransitionName = 'plate';
  const transition = document.startViewTransition(
    () =>
      new Promise<void>((resolve) => {
        // useRoute commits synchronously on hashchange, so the new DOM exists when this resolves.
        addEventListener('hashchange', () => resolve(), { once: true });
        go();
      }),
  );
  await transition.finished;
  if (from) from.style.viewTransitionName = '';
}

/** Props for an <a> that opens a page with the transition, while keeping middle-click and ctrl-click. */
export function pageLink(path: string, plate?: () => HTMLElement | null) {
  return {
    href: pageHref(path),
    onClick: (e: MouseEvent) => {
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
      e.preventDefault();
      openPage(path, plate?.() ?? undefined);
    },
  };
}
