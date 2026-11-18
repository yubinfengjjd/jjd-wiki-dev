import { imageOf, TYPE_LABEL } from './api';
import type {
  AttachedViz,
  DataDomainGroup,
  GraphData,
  ImplementationStatus,
  MethodHubCard,
  MethodMeta,
  MethodTaxonomy,
  PageMeta,
  PageSummary,
  PageType,
  PortabilityState,
  RuntimeFacts,
  RuntimeMode,
  TaxonomyCount,
  TemplateMeta,
} from './api';
import type { Flow } from './flow';
import { methodFigures } from './figureModels';

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

export const CANONICAL_DATA_DOMAINS: readonly [string, string][] = [
  ['single-cell', '单细胞转录组'],
  ['spatial-omics', '空间转录组'],
  ['bulk-transcriptomics', 'Bulk 转录组'],
  ['genomics-epigenomics', '基因组与表观遗传'],
  ['clinical-prognosis', '临床与预后建模'],
  ['multi-omics', '多组学整合与泛癌'],
  ['general-viz-stats', '通用绘图与统计'],
];

export const DATA_DOMAIN_LABEL: Record<string, string> = Object.fromEntries(CANONICAL_DATA_DOMAINS);

const LEGACY_TAG_TO_DOMAIN: Record<string, string> = {
  'single-cell': 'single-cell',
  '单细胞分析': 'single-cell',
  'spatial-omics': 'spatial-omics',
  '空间转录组': 'spatial-omics',
  'bulk-transcriptomics': 'bulk-transcriptomics',
  'genomics-epigenomics': 'genomics-epigenomics',
  'clinical-prognosis': 'clinical-prognosis',
  'survival-analysis': 'clinical-prognosis',
  '生存分析': 'clinical-prognosis',
  'diagnostic-roc': 'clinical-prognosis',
  '诊断与预测评价': 'clinical-prognosis',
  'multi-omics': 'multi-omics',
  '多组学整合': 'multi-omics',
  '多组学整合与泛癌': 'multi-omics',
  'general-viz-stats': 'general-viz-stats',
  'experimental-statistics': 'general-viz-stats',
  '实验统计': 'general-viz-stats',
};

export function domainsForMeta(meta: { data_domains?: string[]; tags?: string[] }): string[] {
  const explicit = (meta.data_domains ?? []).filter((d) => d in DATA_DOMAIN_LABEL);
  if (explicit.length > 0) return [...new Set(explicit)];
  const mapped: string[] = [];
  for (const tag of meta.tags ?? []) {
    const domain = LEGACY_TAG_TO_DOMAIN[tag.trim()];
    if (domain && !mapped.includes(domain)) mapped.push(domain);
  }
  return mapped;
}

export function domainLabel(slug: string, taxonomy?: MethodTaxonomy): string {
  return taxonomy?.domain_labels?.[slug] ?? DATA_DOMAIN_LABEL[slug] ?? slug;
}

export function dataDomainGroups(taxonomy: MethodTaxonomy, pages?: PageSummary[]): DataDomainGroup[] {
  if (taxonomy.data_domains?.length) return taxonomy.data_domains;
  const analysisPages = (pages ?? []).filter(
    (p): p is PageSummary<MethodMeta> =>
      p.meta.type === 'method' && p.meta.method_kind === 'analysis' && p.meta.status !== 'archived',
  );
  return CANONICAL_DATA_DOMAINS.map(([value, label]) => {
    const members = analysisPages.filter((p) => domainsForMeta(p.meta).includes(value));
    const purposeCounts = new Map<string, number>();
    for (const member of members) {
      for (const purpose of new Set(member.meta.purposes ?? [])) {
        purposeCounts.set(purpose, (purposeCounts.get(purpose) ?? 0) + 1);
      }
    }
    const purposes = [...purposeCounts.entries()].map(([p, count]) => ({ value: p, count }));
    return { value, label, count: members.length, purposes };
  });
}

/** Backend counts decide what exists; an unavailable purpose resets when the domain changes. */
export function purposeOptionsFor(taxonomy: MethodTaxonomy, domain = ''): TaxonomyCount[] {
  if (!domain) return taxonomy.purposes;
  const fromCanonical = taxonomy.data_domains?.find(item => item.value === domain)?.purposes;
  if (fromCanonical) return fromCanonical;
  return taxonomy.domains.find(item => item.value === domain)?.purposes ?? [];
}

export function normalizeMethodSelection(selection: MethodSelection, taxonomy: MethodTaxonomy): MethodSelection {
  const validDomains = new Set([
    ...(taxonomy.data_domains ?? []).map(item => item.value),
    ...taxonomy.domains.map(item => item.value),
  ]);
  const domain = validDomains.has(selection.domain) ? selection.domain : '';
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
    if (selected.domain) {
      const canonical = domainsForMeta(meta);
      const matchesDomain = canonical.includes(selected.domain) || (meta.tags ?? []).includes(selected.domain);
      if (!matchesDomain) return false;
    }
    if (selected.purpose && !(meta.purposes ?? []).includes(selected.purpose)) return false;
    if (query) {
      const haystack = [meta.id, meta.title, meta.summary ?? '', ...(meta.purposes ?? []),
        ...(meta.data_domains ?? []), ...(meta.keywords ?? []), ...(meta.tags ?? []),
        ...(meta.inputs ?? []), ...(meta.outputs ?? [])].join(' ').toLowerCase();
      if (!haystack.includes(query)) return false;
    }
    seen.add(page.path);
    return true;
  });
}

/** Derive a synchronous MethodHubCard fallback from AppData pages/graph/flow for SSR & initial paint. */
export function buildFallbackMethodHub(
  page: PageSummary<MethodMeta>,
  pages: PageSummary[],
  graph: GraphData,
  flow: Flow,
): MethodHubCard {
  const { meta } = page;
  const figures = methodFigures(page.path, pages, graph, flow);
  const curated: AttachedViz['curated'] = [];
  const objectCompatible: AttachedViz['object_compatible'] = [];
  const seenTpl = new Set<string>();

  for (const fig of figures) {
    if (fig.meta.type !== 'template') continue;
    const tpl = fig.meta as TemplateMeta;
    const isPrimary = tpl.primary_method === meta.id || tpl.primary_method === page.path;
    if (fig.relation === 'semantic' || isPrimary) {
      seenTpl.add(tpl.id);
      curated.push({
        id: tpl.id,
        title: tpl.title,
        path: fig.path,
        status: tpl.status,
        language: tpl.language,
        chart_types: tpl.chart_types ?? [],
        tables: [],
        preview_url: imageOf(tpl),
        primary: isPrimary,
        compatibility: fig.semantic?.compatibility ?? 'unreviewed',
        verification: fig.semantic?.verification ?? {
          state: 'not_run',
          scope: '仅声明 primary_method，尚未在方法页 figure_relations 完成语义配对审查。',
          evidence: [],
        },
        reason: fig.semantic?.reason ?? '',
        adaptation: fig.semantic?.adaptation ?? '',
        prerequisites: fig.semantic?.prerequisites ?? [],
      });
    } else if (fig.relation === 'compatible') {
      seenTpl.add(tpl.id);
      objectCompatible.push({
        id: tpl.id,
        title: tpl.title,
        path: fig.path,
        status: tpl.status,
        language: tpl.language,
        chart_types: tpl.chart_types ?? [],
        tables: [],
        preview_url: imageOf(tpl),
        match_type: 'full',
        matched_interfaces: meta.outputs ?? [],
        missing_required_interfaces: [],
      });
    }
  }

  const allPreviews: AttachedViz['all_previews'] = [
    ...curated.map((c) => ({
      id: c.id,
      title: c.title,
      path: c.path,
      preview_url: c.preview_url,
      source: 'curated',
      primary: c.primary,
      compatibility: c.compatibility,
      match_type: null,
      chart_types: c.chart_types,
      language: c.language,
    })),
    ...objectCompatible.map((o) => ({
      id: o.id,
      title: o.title,
      path: o.path,
      preview_url: o.preview_url,
      source: 'object_compatible',
      primary: false,
      compatibility: null,
      match_type: o.match_type,
      chart_types: o.chart_types,
      language: o.language,
    })),
  ].slice(0, 6);

  const domains = domainsForMeta(meta);
  return {
    id: meta.id,
    title: meta.title,
    path: page.path,
    status: meta.status,
    summary: meta.summary ?? '',
    data_domains: domains,
    data_domain_labels: domains.map((d) => DATA_DOMAIN_LABEL[d] ?? d),
    purposes: meta.purposes ?? [],
    tags: meta.tags ?? [],
    keywords: meta.keywords ?? [],
    inputs: meta.inputs ?? [],
    outputs: meta.outputs ?? [],
    data_contract: meta.data_contract ?? {},
    render_bridges: meta.render_bridges ?? [],
    implementations: meta.implementations ?? [],
    implementation_status: page.implementation_status ?? [],
    workflow: page.workflow ?? null,
    next_steps_count: meta.next_steps?.length ?? 0,
    attached_visualizations: {
      curated,
      object_compatible: objectCompatible,
      render_bridged: [],
      all_previews: allPreviews,
    },
    reference_recipes: [],
    unmapped_recipes_count: 0,
  };
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
