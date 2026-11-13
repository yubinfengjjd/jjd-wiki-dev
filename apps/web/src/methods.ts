import { TYPE_LABEL } from './api';
import type { ImplementationStatus, MethodMeta, MethodTaxonomy, PageMeta, PageSummary, PageType, PortabilityState, RuntimeFacts, RuntimeMode, TaxonomyCount } from './api';

export const RUNTIME_MODE_LABEL: Record<RuntimeMode, string> = {
  standalone: '独立模块',
  bundle: '需完整来源库',
  unknown: '未登记运行清单',
};
export const PORTABILITY_LABEL: Record<PortabilityState, string> = {
  verified: '独立迁移已验证',
  declared: '独立声明，尚未验证',
  not_run: '独立声明未运行',
  stale: '独立性证据已过期',
  invalid: '独立性证据无效',
  bundle: '仍需完整来源库',
  unknown: '独立性未登记',
};
export const runtimeModeLabel = (runtime?: RuntimeFacts | null) => RUNTIME_MODE_LABEL[runtime?.mode ?? 'unknown'];
export const portabilityLabel = (runtime?: RuntimeFacts | null) => PORTABILITY_LABEL[runtime?.portability?.state ?? 'unknown'];
export const allPackages = (runtime?: RuntimeFacts | null) => {
  if (!runtime) return [] as string[];
  return [...new Set(Object.values(runtime.required_packages ?? {}).flat())];
};
/** Keep language ownership visible for mixed R/Python implementations. */
export const packageFacts = (runtime?: RuntimeFacts | null) => {
  if (!runtime) return '';
  return Object.entries(runtime.required_packages ?? {})
    .filter(([, packages]) => packages.length > 0)
    .map(([language, packages]) => `${language}: ${packages.join('、')}`)
    .join('；');
};

/** v2 declared conditions: shown as requirements, never as satisfied facts. */
export const conditionFacts = (runtime?: RuntimeFacts | null) => {
  if (!runtime) return [] as string[];
  const facts: string[] = [];
  for (const tool of runtime.tools ?? []) {
    facts.push(`工具 ${tool.name}${tool.version_constraint ? `（${tool.version_constraint}）` : ''}${tool.platform ? ` @ ${tool.platform}` : ''}${tool.condition ? `（条件 ${tool.condition}）` : ''}`);
  }
  for (const resource of runtime.external_resources ?? []) {
    facts.push(`外部资源 ${resource.name}（${resource.role}）`);
  }
  const hardware = runtime.hardware;
  if (hardware && Object.keys(hardware).length > 0) {
    const parts = [hardware.accelerator ? `加速 ${hardware.accelerator}` : '',
      hardware.min_memory_gb ? `内存 ≥${hardware.min_memory_gb}GB` : '',
      hardware.min_vram_gb ? `显存 ≥${hardware.min_vram_gb}GB` : '',
      hardware.min_cpu_cores ? `CPU ≥${hardware.min_cpu_cores}核` : ''].filter(Boolean);
    if (parts.length || hardware.condition) {
      const qualifier = hardware.condition ? `（条件 ${hardware.condition}）` : '';
      facts.push(parts.length ? `硬件 ${parts.join('、')}${qualifier}` : `硬件${qualifier}`);
    }
    if (hardware.notes) facts.push(`硬件说明 ${hardware.notes}`);
  }
  if (runtime.invocation?.command) facts.push(`调用 ${runtime.invocation.command}`);
  return facts;
};
export const ENTRY_KIND_LABEL: Record<string, string> = {
  function: '函数入口', script: '脚本入口', external_program: '外部程序入口',
};
export const entryKindLabel = (runtime?: RuntimeFacts | null) =>
  ENTRY_KIND_LABEL[runtime?.entry_kind ?? ''] ?? null;

export const METHOD_KIND_LABEL = { analysis: '分析家族', workflow: '组合流程', technical: '技术资料' };
export const methodKindLabel = (meta: MethodMeta) => meta.method_kind ? METHOD_KIND_LABEL[meta.method_kind] ?? '待分类' : '待分类';

/** `type: method` is the storage type; only method_kind says analysis/workflow/technical. */
export function pageTypeLabel(meta: PageMeta | undefined, fallback?: PageType): string {
  if (meta?.type === 'method') return methodKindLabel(meta);
  return TYPE_LABEL[meta?.type ?? fallback ?? 'method'];
}
export const IMPLEMENTATION_LABEL: Record<ImplementationStatus['state'], string> = {
  verified: '已验证', not_run: '未运行', stale: '验证已过期', invalid: '验证无效',
};

/** Only an explicitly declared branch with a current backend result counts as verified. */
export function verifiedImplementations(meta: MethodMeta, statuses: ImplementationStatus[] = []) {
  return (meta.implementations ?? []).filter(implementation => statuses.some(status => status.id === implementation.id && status.state === 'verified'));
}

/** URL state for the two-level directory. Domain and purpose remain independent filters. */
export interface MethodSelection {
  domain: string;
  purpose: string;
  q: string;
}

export function parseMethodQuery(query = ''): MethodSelection {
  const params = new URLSearchParams(query.replace(/^\?/, ''));
  return { domain: params.get('domain') ?? '', purpose: params.get('purpose') ?? '', q: params.get('q') ?? '' };
}

export function methodSelectionHref(selection: MethodSelection): string {
  const params = new URLSearchParams();
  if (selection.domain) params.set('domain', selection.domain);
  if (selection.purpose) params.set('purpose', selection.purpose);
  if (selection.q) params.set('q', selection.q);
  const query = params.toString();
  return query ? `#/methods?${query}` : '#/methods';
}

/** Backend counts decide what exists; an unavailable purpose resets when the domain changes. */
export function purposeOptionsFor(taxonomy: MethodTaxonomy, domain = ''): TaxonomyCount[] {
  if (!domain) return taxonomy.purposes;
  return taxonomy.domains.find(item => item.value === domain)?.purposes ?? [];
}

export function normalizeMethodSelection(selection: MethodSelection, taxonomy: MethodTaxonomy): MethodSelection {
  const domain = taxonomy.domains.some(item => item.value === selection.domain) ? selection.domain : '';
  const purposes = purposeOptionsFor(taxonomy, domain).map(item => item.value);
  const purpose = purposes.includes(selection.purpose) ? selection.purpose : '';
  return { domain, purpose, q: selection.q };
}

/** Analysis pages only; a page with several tags/purposes is still one result. */
export function filterAnalysisMethods(
  pages: PageSummary[],
  taxonomy: MethodTaxonomy,
  selection: MethodSelection,
): PageSummary<MethodMeta>[] {
  const selected = normalizeMethodSelection(selection, taxonomy);
  const query = selected.q.trim().toLowerCase();
  const seen = new Set<string>();
  return pages.filter((page): page is PageSummary<MethodMeta> => {
    const meta = page.meta;
    if (meta.type !== 'method' || meta.method_kind !== 'analysis' || meta.status === 'archived') return false;
    if (seen.has(page.path)) return false;
    if (selected.domain && !(meta.tags ?? []).includes(selected.domain)) return false;
    if (selected.purpose && !(meta.purposes ?? []).includes(selected.purpose)) return false;
    if (query) {
      const haystack = [meta.id, meta.title, meta.summary ?? '', ...(meta.purposes ?? []),
        ...(meta.keywords ?? []), ...(meta.tags ?? [])].join(' ').toLowerCase();
      if (!haystack.includes(query)) return false;
    }
    seen.add(page.path);
    return true;
  });
}

export type MethodBrowseKind = 'all' | 'analysis' | 'workflow' | 'technical';
export function methodBrowseKind(query = ''): MethodBrowseKind {
  const params = new URLSearchParams(query.replace(/^\?/, ''));
  const value = params.get('kind');
  if (value === 'all' || value === 'analysis' || value === 'workflow' || value === 'technical') return value;
  return params.has('domain') || params.has('purpose') ? 'analysis' : 'all';
}
export function matchesMethodQuery(meta: MethodMeta, query: string): boolean {
  const words = [meta.id, meta.title, meta.summary ?? '', ...(meta.purposes ?? []),
    ...(meta.tags ?? []), ...(meta.keywords ?? []), ...(meta.cite ?? []),
    ...(meta.implementations ?? []).flatMap(i => [i.id, i.title, i.entrypoint, ...i.dependencies])];
  const text = words.join(' ').toLowerCase();
  return query.toLowerCase().split(/\s+/).filter(Boolean).every(word => text.includes(word));
}
export function plottingCodePages(pages: PageSummary[]): PageSummary<MethodMeta>[] {
  const seen = new Set<string>();
  return pages.filter((page): page is PageSummary<MethodMeta> => {
    if (page.meta.type !== 'method' || page.meta.status === 'archived'
      || !page.meta.code_roles?.includes('visualization') || !page.meta.implementations?.length || seen.has(page.path)) return false;
    seen.add(page.path);return true;
  });
}
