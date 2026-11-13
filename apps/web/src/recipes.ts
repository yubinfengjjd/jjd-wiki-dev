import { isItem, workflowOf } from './api';
import type { PageSummary, PageType, RecipeMeta, ScenarioPick } from './api';

export function matchesRecipeQuery(meta: RecipeMeta, origin: string, query: string): boolean {
  const text = [meta.id, meta.title, meta.summary ?? '', origin,
    ...(meta.tags ?? []), ...(meta.keywords ?? []), ...(meta.chart_types ?? []),
    ...(meta.inputs ?? []).map(input => input.file)].join(' ').toLowerCase();
  return query.toLowerCase().split(/\s+/).filter(Boolean).every(word => text.includes(word));
}

/** SPDX ids such as CC-BY-NC-SA-4.0 carry an `NC` token; the permissive `NCSA` licence does not. */
export const isNonCommercial = (license: string | null | undefined): boolean =>
  (license ?? '').split(/[-_.\s]+/).some((token) => token.toUpperCase() === 'NC');

export function licenseLabel(license: string | null | undefined): string {
  if (isNonCommercial(license)) return '非商业';
  if (!license || license === 'none') return '无许可证';
  return license;
}

/** Census and filter keys are the backend workflow stages; cards show the backend label (待装包 / 待补齐 …). */
export const RECIPE_STAGES: [string, string][] = [
  ['complete', '可原样运行'],
  ['repair_complete', '修补版运行通过'],
  ['recipe_confirm', '原样运行通过 · 待确认'],
  ['recipe_work', '等 agent 处理'],
];

export const recipeStage = (meta: RecipeMeta): string =>
  workflowOf(meta)?.stage ?? (meta.status === 'ready' ? 'complete' : meta.status);

/** "FigureYa · FigureYa59volcanoV2": the source library's page title when known, then the upstream item. */
export function recipeOrigin(meta: RecipeMeta, titles: Map<string, string>): string {
  const source = meta.source ?? ({} as Partial<RecipeMeta['source']>);
  const library = (source.id && titles.get(`sources/${source.id}.md`)) || source.id;
  return [library, source.item].filter(Boolean).join(' · ');
}

export interface ResolvedPick {
  id: string;
  note: string;
  /** Wiki page the pick names, when it exists. */
  path: string | null;
  title: string;
  type: PageType | null;
  /** An L0 catalog item (`<source>:<item>`): listed upstream, not run in the Wiki. */
  catalog: boolean;
  archived: boolean;
}

/** Same lookup as the backend facts table: a page path, a bare page id, or an L0 catalog id. */
export function resolvePick(pick: ScenarioPick | string, pages: PageSummary[]): ResolvedPick {
  const id = typeof pick === 'string' ? pick : String(pick?.id ?? '');
  const note = typeof pick === 'string' ? '' : pick?.note ?? '';
  const missing = { id, note, path: null, title: id, type: null, archived: false };
  if (id.includes(':')) return { ...missing, catalog: true };
  const candidates = id.includes('/')
    ? [id.endsWith('.md') ? id : `${id}.md`]
    : ['recipes', 'templates', 'methods'].map((dir) => `${dir}/${id}.md`);
  const page = candidates.map((path) => pages.find((p) => p.path === path)).find(Boolean);
  if (!page) return { ...missing, catalog: false };
  return { id, note, path: page.path, title: page.meta.title, type: page.meta.type, catalog: false,
    archived: isItem(page.meta) && page.meta.status === 'archived' };
}
