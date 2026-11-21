import { isFigure, LayoutMeta, PageSummary, TemplateMeta, GraphData, Relation, displayStatus } from './api';
import type { Flow } from './flow';

export type FigureMeta = LayoutMeta | TemplateMeta;
export type FigureShelf = 'single' | 'template';

export interface OutputSlotGroup<T> {
  slotKey: string;
  primaryMethod: string;
  primaryChart: string;
  items: T[];
  defaultItem: T;
}

type SlotCandidate = {
  path: string;
  meta: FigureMeta;
};

function slotItemRank(meta: FigureMeta): [number, number, string] {
  const tierRank = meta.type === 'template' && meta.style_tier === 'default'
    ? 0
    : meta.type === 'template' && meta.style_tier !== 'variant'
      ? 1
      : 2;
  const statusRank = meta.status === 'ready' ? 0 : 1;
  return [tierRank, statusRank, meta.id];
}

export function groupByOutputSlot<T extends SlotCandidate>(items: T[]): OutputSlotGroup<T>[] {
  const buckets = new Map<string, { primaryMethod: string; primaryChart: string; items: T[] }>();
  for (const item of items) {
    const pm = item.meta.type === 'template' ? (item.meta.primary_method ?? '').trim() : '';
    const ct = (item.meta.chart_types?.[0] ?? '').trim();
    const isSlotted = Boolean(pm && ct);
    const slotKey = isSlotted ? `${pm}::${ct}` : `single::${item.path}`;
    let bucket = buckets.get(slotKey);
    if (!bucket) {
      bucket = { primaryMethod: pm, primaryChart: ct, items: [] };
      buckets.set(slotKey, bucket);
    }
    bucket.items.push(item);
  }
  const groups: OutputSlotGroup<T>[] = [];
  for (const [slotKey, bucket] of buckets.entries()) {
    const sorted = [...bucket.items].sort((a, b) => {
      const [ta, sa, ia] = slotItemRank(a.meta);
      const [tb, sb, ib] = slotItemRank(b.meta);
      return ta - tb || sa - sb || ia.localeCompare(ib);
    });
    groups.push({
      slotKey,
      primaryMethod: bucket.primaryMethod,
      primaryChart: bucket.primaryChart,
      items: sorted,
      defaultItem: sorted[0],
    });
  }
  return groups;
}

export interface StylePillSubject {
  id: string;
  title: string;
  style_tier?: 'default' | 'variant';
  journal_style?: string;
}

function baseStyleLabel(item: StylePillSubject): string {
  const journal = (item.journal_style ?? '').trim();
  if (item.style_tier === 'default') {
    if (!journal || journal === 'Standard') return 'Standard 默认';
    return `${journal} 默认`;
  }
  if (journal) return journal;
  return item.title || item.id;
}

export function stylePillLabel(item: StylePillSubject, siblings: StylePillSubject[]): string {
  const base = baseStyleLabel(item);
  const dupCount = siblings.filter((s) => baseStyleLabel(s) === base).length;
  if (dupCount <= 1) return base;
  const shortTitle = (item.title || item.id).slice(0, 10);
  return `${base} · ${shortTitle}`;
}

/** Search provenance as well as the display title; translated titles often omit the library name. */
export function matchesFigureQuery(meta: FigureMeta, query: string, pages: PageSummary[]): boolean {
  const byPath = new Map(pages.map(p => [p.path, p.meta]));
  const words = [
    meta.id,
    meta.title,
    ...(meta.tags ?? []),
    ...(meta.chart_types ?? []),
    ...(meta.type === 'template' && meta.journal_style ? [meta.journal_style] : []),
    ...('keywords' in meta && Array.isArray(meta.keywords) ? meta.keywords.map(String) : []),
  ];
  if (meta.type === 'template') {
    for (const reference of meta.sources ?? []) {
      words.push(reference);
      const source = byPath.get(reference.endsWith('.md') ? reference : `${reference}.md`);
      if (source) words.push(source.title);
      if (source?.type === 'recipe') {
        words.push(source.source?.id ?? '', source.source?.item ?? '');
        const library = byPath.get(`sources/${source.source?.id}.md`);
        if (library) words.push(library.title);
      }
    }
  }
  const text = words.join(' ').toLowerCase();
  return query.toLowerCase().split(/\s+/).filter(Boolean).every(word => text.includes(word));
}

export function isWholeSource(meta: PageSummary['meta']): boolean {
  return meta.type === 'layout' && Object.keys(meta.panels).length !== 1;
}

export function singlePanelKnowledge(pages: PageSummary[], graph: GraphData) {
  const hidden = new Set(pages.filter((p) => isWholeSource(p.meta)).map((p) => p.path));
  return {
    hiddenSources: hidden,
    pages: pages.filter((p) => !hidden.has(p.path)),
    graph: { nodes: graph.nodes.filter((n) => !hidden.has(n.id)),
      links: graph.links.filter((e) => !hidden.has(e.source) && !hidden.has(e.target)) },
  };
}
export interface MethodFigure {
  path: string;
  meta: FigureMeta;
  relation: 'semantic' | 'compatible' | 'reference';
  semantic?: Relation;
  sourceLinks?: SourceLink[];
}
export interface SourceLink { path: string; title: string }

/** In a method's associated-figure card, qualify a bare '可用' so template
 * availability is not read as availability of an unverified analysis. */
export function methodFigureStatusLabel(figure: MethodFigure): string {
  const label = displayStatus(figure.meta);
  if (label !== '可用') return label;
  return figure.meta.type === 'template' ? '图模板可用' : '图样可用';
}

function coversSource(template: TemplateMeta, source: LayoutMeta): boolean {
  const letters = source.template_panels[template.id] ?? [];
  const chartTypes = template.chart_types ?? [];
  return (template.layouts ?? []).includes(source.id) && source.templates.includes(template.id)
    && source.templates.length === 1 && Object.keys(source.template_panels).length === 1
    && Object.keys(source.panels).length > 0 && letters.length === Object.keys(source.panels).length
    && chartTypes.length === 1
    && Object.keys(source.panels).every((p) => letters.includes(p) && source.panels[p] === chartTypes[0]);
}

/** Only proven full coverage connects a source to a callable style. */
function figureGroups<T extends { path: string; meta: FigureMeta }>(figures: T[]): T[][] {
  const templates = figures.filter((p) => p.meta.type === 'template');
  const grouped = new Map(templates.map((p) => [p.path, [p]]));
  const singles: T[][] = [];
  for (const source of figures.filter((p) => p.meta.type === 'layout')) {
    const match = templates.find((t) => t.meta.type === 'template' && source.meta.type === 'layout' && coversSource(t.meta, source.meta));
    if (match) grouped.get(match.path)!.push(source);
    else singles.push([source]);
  }
  return [...singles, ...grouped.values()];
}
const sourceLinks = (group: { path: string; meta: FigureMeta }[]): SourceLink[] => group.filter((p) => p.meta.type === 'layout').map((p) => ({ path: p.path, title: p.meta.title }));

/** Style and callable are overlapping views, not exclusive storage types. */
export function galleryEntries(pages: PageSummary[]) {
  const figures = pages.filter((p): p is PageSummary<FigureMeta> => isFigure(p.meta) && p.meta.status !== 'archived' && !isWholeSource(p.meta));
  const sources = figures.filter((p): p is PageSummary<LayoutMeta> => p.meta.type === 'layout');
  const templates = figures.filter((p): p is PageSummary<TemplateMeta> => p.meta.type === 'template');
  const representatives = figureGroups(figures).map((group) => ({
    ...(group.find((p) => p.meta.type === 'layout') ?? group[0]), sourceLinks: sourceLinks(group),
  }));
  const order = new Map(figures.map((p, i) => [p.path, i]));
  return {
    single: representatives.sort((a, b) => order.get(a.path)! - order.get(b.path)!),
    template: templates.map((p) => ({ ...p, sourceLinks: sources.filter((s) => coversSource(p.meta, s.meta)).map((s) => ({ path: s.path, title: s.meta.title })) })),
  };
}

export function figureLabel(meta: FigureMeta): string {
  return meta.type === 'template' ? '可调用模板' : '单 panel 图样';
}

export function methodPlateFigures(figures: MethodFigure[]): MethodFigure[] {
  const priority = (f: MethodFigure) => f.relation === 'semantic' ? 0 : f.relation === 'reference' ? 1 : 2;
  return methodDisplayFigures(figures).sort((a, b) => priority(a) - priority(b)).slice(0, 3);
}

/** Merge only an explicitly covered source with its template, preserving all raw relations. */
export function methodDisplayFigures(figures: MethodFigure[]): MethodFigure[] {
  return figureGroups(figures).map((group) => ({
    ...(group.find((p) => p.meta.type === 'template') ?? group[0]), sourceLinks: sourceLinks(group),
  }));
}

export function templateSourceNote(meta: TemplateMeta, pages: PageSummary[], hiddenSources: Set<string> = new Set()): string {
  // v2 templates may carry no layouts at all; their provenance is a Wiki page in `sources`.
  const sources = (meta.layouts ?? []).map((id) => `layouts/${id}.md`);
  if (sources.some((path) => pages.some((p) => p.path === path && p.meta.type === 'layout' && !isWholeSource(p.meta)))) {
    return '来源：已收录单 panel 图样';
  }
  if (sources.some((path) => hiddenSources.has(path))) return '历史单 panel 模板 · 整图来源已归档';
  const recipes = (meta.sources ?? []).filter((s) => s.startsWith('recipes/')).map((s) => (s.endsWith('.md') ? s : `${s}.md`));
  if (recipes.some((path) => pages.some((p) => p.path === path && p.meta.type === 'recipe'))) return '来源：历史归档模板';
  return '来源记录待核查';
}

export function galleryInventory(pages: PageSummary[], hiddenSources: Set<string> = new Set()) {
  const templates = pages.filter((p): p is PageSummary<TemplateMeta> => p.meta.type === 'template' && p.meta.status !== 'archived');
  return {
    styles: galleryEntries(pages).single.length,
    sources: pages.filter((p) => p.meta.type === 'layout' && p.meta.status !== 'archived' && !isWholeSource(p.meta)).length,
    templates: templates.length,
    historical: templates.filter((p) => templateSourceNote(p.meta, pages, hiddenSources).startsWith('历史')).length,
  };
}

/** Compatible tables and explicit Wiki references are different relationships. No tag-only inference. */
export function methodFigures(method: string, pages: PageSummary[], graph: GraphData, flow: Flow): MethodFigure[] {
  const byPath = new Map(pages.map((p) => [p.path, p]));
  const compatible = new Set(flow.figuresOf(method));
  const semantic = new Map((byPath.get(method)?.relations ?? []).filter((r) => r.method === method && r.active).map((r) => [r.figure, r]));
  const declared = byPath.get(method)?.figure_refs;
  const refs = new Set<string>(declared ?? []);
  if (declared === undefined) {
    // Compatibility with older servers; current API preserves outgoing references.
    for (const edge of graph.links) {
      if (edge.kind !== 'link') continue;
      if (edge.source === method) refs.add(edge.target);
      if (edge.target === method) refs.add(edge.source);
    }
  }
  const items: MethodFigure[] = [];
  for (const path of new Set([...semantic.keys(), ...refs, ...compatible])) {
    const page = byPath.get(path);
    if (!page || !isFigure(page.meta) || page.meta.status === 'archived' || isWholeSource(page.meta)) continue;
    items.push({ path, meta: page.meta, relation: semantic.has(path) ? 'semantic' : refs.has(path) ? 'reference' : 'compatible', semantic: semantic.get(path) });
  }
  return items.sort((a, b) => {
    const rank = (f: MethodFigure) => f.relation === 'semantic' ? 0 : f.relation === 'reference' ? 1 : 2;
    return rank(a) - rank(b) || a.path.localeCompare(b.path);
  });
}
