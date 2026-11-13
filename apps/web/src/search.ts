import { pageHref, SearchResult } from './api';

export interface SearchSelection { q: string; kind: string; scope: 'knowledge' | 'source'; runnable: boolean }
export function parseSearchQuery(query: string): SearchSelection {
  const params = new URLSearchParams(query);
  return {q: params.get('q') ?? '', kind: params.get('kind') ?? '',
    scope: params.get('scope') === 'source' ? 'source' : 'knowledge', runnable: params.get('runnable') === 'true'};
}
export function searchParams(selection: SearchSelection) {
  return new URLSearchParams({q: selection.q, kind: selection.kind, scope: selection.scope,
    runnable: String(selection.runnable), limit: '20'});
}
export const searchHref = (selection: SearchSelection) => `#/search?${searchParams(selection)}`;
export function searchResultHref(result: Pick<SearchResult, 'page' | 'match_section'>) {
  return result.page ? pageHref(result.page) + (result.match_section ? `?${new URLSearchParams({section: result.match_section})}` : '') : '';
}
/** Canonical sections presented once by the method overview retain their target. */
export function sectionTargets(section: string) {
  const aliases: Record<string, string> = {用途: '研究问题与用途', 输入: '输入对象', 输出: '输出对象'};
  return [section.trim(), aliases[section.trim()]].filter(Boolean);
}

/** Abort old I/O and also guard callbacks: servers may finish after cancellation. */
export function latestSearch<T>() {
  let controller: AbortController | undefined;
  let generation = 0;
  const cancel = () => { generation++; controller?.abort(); };
  const run = async (load: (signal: AbortSignal) => Promise<T>, publish: (value: T) => void, fail: (error: Error) => void) => {
    cancel();
    const own = generation;
    controller = new AbortController();
    try { const value = await load(controller.signal); if (own === generation) publish(value); }
    catch (error) { if (own === generation) fail(error as Error); }
  };
  run.cancel = cancel;
  return run;
}
