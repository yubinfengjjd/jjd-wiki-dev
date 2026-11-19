export type Status = 'pending_signoff' | 'pending_template' | 'draft' | 'ready' | 'archived';
export type PageType = 'layout' | 'template' | 'method' | 'interface' | 'chart-type' | 'project'
  | 'recipe' | 'source' | 'scenario';
/** Page types the author acts on; each has its own status machine and the shared favorite/note/tags/archive endpoints. */
export type Kind = 'layouts' | 'templates' | 'methods' | 'recipes';

export type Compatibility = 'direct' | 'adaptable' | 'candidate';
export interface Verification {
  state: string;
  scope?: string;
  evidence?: string[];
}
/** The same semantic record is returned on both the method and figure page. */
export interface Relation {
  method: string;
  figure: string;
  method_title: string;
  figure_title: string;
  method_status: Status;
  figure_status: Status;
  compatibility: Compatibility;
  reason: string;
  prerequisites: string[];
  adaptation: string;
  evidence: string[];
  verification: Verification;
  target_kind: 'template' | 'layout';
  active: boolean;
}
export type CodeVariant = 'original' | 'reusable';
export type RuntimeMode = 'standalone' | 'bundle' | 'unknown';
export type PortabilityState = 'verified' | 'declared' | 'not_run' | 'stale' | 'invalid' | 'unknown' | 'bundle';
export interface RuntimeResource { path: string; sha256: string | null; role: string }
export interface RuntimePortability {
  state: PortabilityState;
  scope: string;
  evidence: string | null;
  closure_hash: string | null;
  issues?: string[];
}
export interface RuntimeTool {
  name: string;
  version_constraint?: string;
  platform?: string;
  /** Declared gate for when this tool is required; display only. */
  condition?: string;
  notes?: string;
}
export interface RuntimeExternalResource {
  name: string;
  role: string;
  source?: string;
  sha256?: string;
}
export interface RuntimeHardware {
  accelerator?: 'cpu' | 'gpu' | 'tpu';
  min_memory_gb?: number;
  min_vram_gb?: number;
  min_cpu_cores?: number;
  /** Declared gate for when this hardware is required; display only. */
  condition?: string;
  notes?: string;
}
export interface RuntimeFacts {
  id?: string;
  mode: RuntimeMode;
  declared: boolean;
  entry?: string | null;
  /** v2: 'function' | 'script' | 'external_program'; absent on old manifests. */
  entry_kind?: string | null;
  entry_function?: string | null;
  language?: string | null;
  files: string[];
  resources: RuntimeResource[];
  required_packages: Record<string, string[]>;
  optional_packages: Record<string, Record<string, string>>;
  /** v2 declared conditions: display only, never grant verification. */
  tools?: RuntimeTool[];
  external_resources?: RuntimeExternalResource[];
  hardware?: RuntimeHardware;
  invocation?: {command?: string; args?: string[]; env?: Record<string, string>; notes?: string};
  fingerprint_mode?: 'v1' | 'v2' | 'unknown';
  portability: RuntimePortability;
  source?: Record<string, unknown>;
  issues?: string[];
  /** Method pages only: branch id to its runtime fact. */
  implementations?: Record<string, RuntimeFacts>;
}
export interface ImplementationBranch {
  id: string;
  title: string;
  state: 'verified' | 'not_run' | 'stale' | 'invalid';
  scope: string;
  receipt?: string;
  runtime?: RuntimeFacts;
}
export interface CodeFile {
  variant: CodeVariant;
  path: string;
  language: string;
  size: number;
  sha256: string;
  text: boolean;
  source: unknown;
  verification: Verification;
  /** Present for reusable files whose entrypoint belongs to one or more declared branches. */
  branches?: ImplementationBranch[];
}
export interface CodeListing { files: CodeFile[]; note: string; asset_availability?: AssetAvailability; asset_id?: string }
export type AssetAvailability = 'available' | 'not_downloaded' | 'missing';
export interface SearchResult {
  id: string; kind: string; title: string; page: string; summary: string;
  score: number; why: string[]; usable: boolean; run: string;
  match_section: string; snippet: string;
  asset_availability: AssetAvailability; evidence_state: string;
  source_path?: string; file_path?: string; asset_id?: string;
  source_scope?: boolean;
}
export interface SearchResponse {
  results: SearchResult[];
  coverage: Record<string, unknown>;
  index: Record<string, unknown>;
}
export interface CodeText {
  path: string;
  variant: CodeVariant;
  language: string;
  text: string | null;
  encoding: string | null;
  note: string;
  sha256: string;
  size: number;
}

interface ItemBase {
  id: string;
  title: string;
  status: Status;
  /** Free tags that help search; they never restrict where an item can be used. */
  tags: string[];
  favorite: boolean;
  archived_from?: Status;
}

export interface LayoutMeta extends ItemBase {
  type: 'layout';
  language: string;
  gallery_entry: string;
  gallery_version: number;
  chart_types: string[];
  panels: Record<string, string>;
  templates: string[];
  template_panels: Record<string, string[]>;
}

export interface TemplateMeta extends ItemBase {
  type: 'template';
  language: string;
  /** Legacy provenance; v2 templates may have none and record `sources` instead. */
  layouts?: string[];
  /** v2 provenance as Wiki pages, e.g. `recipes/<id>`. */
  sources?: string[];
  /** May be empty for v2 templates derived from a recipe. */
  panels: string[];
  chart_types: string[];
  primary_method?: string;
  style_tier?: 'default' | 'variant';
  journal_style?: string;
  aliases?: string[];
  data_domains?: string[];
}

/** Legacy read-only recipe archive: whole upstream module kept byte-for-byte. */
export interface RecipeMeta extends ItemBase {
  type: 'recipe';
  source: { id: string; item: string; commit: string; url?: string };
  license: string;
  cite?: string[];
  language: string;
  runner?: string;
  entry?: string;
  inputs?: { file: string; note?: string }[];
  outputs?: string[];
  packages?: { cran?: string[]; bioc?: string[]; github?: string[]; library?: string[] };
  keywords?: string[];
  chart_types: string[];
  summary?: string;
}

/** v2 upstream library registration; no status of its own. */
export interface SourceMeta {
  type: 'source';
  id: string;
  title: string;
  url: string;
  commit?: string | null;
  license: string;
  license_notice?: string;
  cite?: string[];
  adapter: string;
  trusted: boolean;
  snapshot?: string;
  tags?: string[];
  keywords?: string[];
  summary?: string;
}

/** A pick names a page path, a bare page id or an L0 catalog item `<source>:<item>`. */
export interface ScenarioPick { id: string; note?: string }

/** v2 research scenario: preferred entries for one research question; no status of its own. */
export interface ScenarioMeta {
  type: 'scenario';
  id: string;
  title: string;
  picks: (ScenarioPick | string)[];
  tags?: string[];
  keywords?: string[];
  summary?: string;
}

export type MethodKind = 'analysis' | 'workflow' | 'technical';
export interface MethodImplementation {
  id: string;
  title: string;
  language: string;
  entrypoint: string;
  dependencies: string[];
  verification?: string;
}
export interface ImplementationStatus {
  id: string;
  title: string;
  state: 'verified' | 'not_run' | 'stale' | 'invalid';
  scope: string;
  runtime?: RuntimeFacts;
}

export interface RenderBridge {
  interface: string;
  from_output: string;
  extractor_note: string;
  unit?: string;
}

export interface AttachedVizTable {
  key: string;
  interface: string;
  description: string;
  required: boolean;
}

export interface AttachedVizCurated {
  id: string;
  title: string;
  path: string;
  kind?: 'template' | 'recipe' | string;
  status: Status;
  language: string;
  license?: string;
  style_tier?: 'default' | 'variant';
  journal_style?: string;
  chart_types: string[];
  tables: AttachedVizTable[];
  preview_url: string | null;
  primary: boolean;
  compatibility: Compatibility | 'unreviewed' | string;
  verification: Verification;
  reason: string;
  adaptation: string;
  prerequisites: string[];
}

export interface AttachedVizCompatible {
  id: string;
  title: string;
  path: string;
  status: Status;
  language: string;
  style_tier?: 'default' | 'variant';
  journal_style?: string;
  chart_types: string[];
  tables: AttachedVizTable[];
  preview_url: string | null;
  match_type: 'full' | 'partial' | string;
  matched_interfaces: string[];
  missing_required_interfaces: string[];
}

export interface AttachedVizBridged {
  id: string;
  title: string;
  path: string;
  status: Status;
  language: string;
  style_tier?: 'default' | 'variant';
  journal_style?: string;
  chart_types: string[];
  tables: AttachedVizTable[];
  preview_url: string | null;
  via_bridge: string;
  from_output: string;
  extractor_note: string;
  unit?: string;
  bridges: RenderBridge[];
  match_type: 'full' | 'partial' | string;
  matched_interfaces: string[];
  missing_required_interfaces: string[];
}

export interface AttachedVizPreview {
  id: string;
  title: string;
  path: string;
  preview_url: string | null;
  source: 'curated' | 'render_bridged' | 'object_compatible' | string;
  primary: boolean;
  compatibility?: string | null;
  match_type?: string | null;
  chart_types: string[];
  language: string;
}

export interface AttachedViz {
  curated: AttachedVizCurated[];
  object_compatible: AttachedVizCompatible[];
  render_bridged: AttachedVizBridged[];
  all_previews: AttachedVizPreview[];
}

export interface ReferenceRecipeSummary {
  id: string;
  title: string;
  path: string;
  status: Status;
  language: string;
  runner: string;
  license?: string;
  chart_types: string[];
  tags: string[];
  data_domains: string[];
  confidence: string;
  note: string;
  methods: string[];
  preview_url: string | null;
}

export interface MethodMeta extends ItemBase {
  type: 'method';
  /** Missing classification remains unclassified; it must not default to analysis. */
  method_kind?: MethodKind;
  /** Explicit browsing roles; do not infer a plot or algorithm from its filename. */
  code_roles?: ('analysis' | 'visualization' | 'runtime')[];
  /** Canonical theory references, not executable compatibility claims. */
  theory_methods?: string[];
  /** Controlled analysis purpose list; discovery only, never an execution gate. */
  purposes?: string[];
  /** Canonical 7 data-type domain slugs. */
  data_domains?: string[];
  aliases?: string[];
  keywords?: string[];
  summary?: string;
  data_contract?: { input: string; output: string };
  render_bridges?: RenderBridge[];
  implementations?: MethodImplementation[];
  /** Interface slugs the analysis reads and the tables it is finally shaped into. */
  inputs: string[];
  outputs: string[];
  next_steps?: NextStepBranch[];
  source:
    | { kind: 'post'; gallery_entry: string }
    | { kind: 'project'; path: string }
    | { kind: 'repo'; url: string; commit: string }
    | { kind: 'written' };
  license: string;
  cite: string[];
}

export interface NextStepBranch {
  branch_id?: string;
  direction: string;
  when: string;
  hypothesis?: string;
  required_object?: string;
  analysis_templates: string[];
  intermediate_interface: string;
  viz_templates: string[];
}

export interface CuratedBranchMethodRef {
  id: string;
  title: string;
  path: string;
  status: Status;
}

export interface CuratedBranchRecipeRef {
  id: string;
  title: string;
  path: string;
  status: Status;
  license?: string;
  preview_url?: string | null;
}

export interface CuratedBranchVizRef {
  id: string;
  title: string;
  path: string;
  status: Status;
  compatibility?: string;
  preview_url?: string | null;
  language?: string;
  chart_types?: string[];
}

export interface CuratedBranchV2 {
  branch_id: string;
  direction: string;
  when: string;
  hypothesis: string;
  required_object: string;
  produced_interface: string;
  next_methods: CuratedBranchMethodRef[];
  reference_recipes: CuratedBranchRecipeRef[];
  viz_templates: CuratedBranchVizRef[];
}

export interface ObjectCandidateV2 {
  id: string;
  kind: 'method' | 'template' | string;
  title: string;
  path: string;
  status: Status;
  source: string;
  match_type: 'full' | 'partial' | string;
  shared_interfaces: string[];
  missing_required_interfaces: string[];
  data_domains?: string[];
  purposes?: string[];
  language?: string;
  chart_types?: string[];
  preview_url?: string | null;
  downstream_viz?: AttachedVizPreview[];
}

export interface NextCurrentNodeV2 {
  id: string;
  requested_id?: string;
  kind: string;
  title: string;
  path: string;
  status: Status;
  data_domains?: string[];
  purposes?: string[];
  inputs?: string[];
  outputs: string[];
}

export interface NextStepsResponse {
  schema_version?: number;
  node_id: string;
  requested_id?: string;
  kind?: string;
  title?: string;
  path?: string;
  page?: string;
  outputs?: string[];
  current_node?: NextCurrentNodeV2;
  decision_mode?: string;
  agent_guidance?: string;
  curated_branches?: CuratedBranchV2[];
  object_compatible_candidates?: ObjectCandidateV2[];
  attached_visualizations?: AttachedViz;
  next_steps: NextStepBranch[];
  structural_matches?: {
    path: string;
    id: string;
    title: string;
    type: string;
    outputs?: string[];
    inputs?: string[];
  }[];
}

export interface PlaybookStep {
  id: string;
  title: string;
  method_id?: string;
  description?: string;
  templates?: string[];
  interface?: string;
  inputs?: string[];
  outputs?: string[];
  requires?: string[];
  external_requires?: string[];
  subtree?: string;
  next?: string[];
}

export interface PlaybookItem {
  id: string;
  title: string;
  path: string;
  summary?: string;
  tags?: string[];
  steps: PlaybookStep[];
  picks?: (ScenarioPick | string)[];
}

export interface PlaybookGraphNode {
  id: string;
  label: string;
  kind: string;
  path?: string;
}

export interface PlaybookGraphEdge {
  source: string;
  target: string;
  label?: string;
}

export interface PlaybooksResponse {
  playbooks: PlaybookItem[];
  scenarios?: PlaybookItem[];
  graph?: { nodes: PlaybookGraphNode[]; edges: PlaybookGraphEdge[] };
}

export interface StudioSniffColumn {
  name: string;
  type: string;
  samples: string[];
}

export interface StudioSniffResponse {
  path?: string;
  columns: StudioSniffColumn[];
  row_count_estimate: number;
  preview_rows: Record<string, string>[];
  note?: string;
}

export interface StudioParamSchema {
  name: string;
  label?: string;
  type: 'select' | 'palette' | 'number' | 'range' | 'float' | 'int' | 'boolean' | 'bool' | 'string' | 'str' | 'text' | string;
  default?: string | number | boolean;
  choices?: string[];
  min?: number;
  max?: number;
  step?: number | null;
  description?: string;
  help?: string;
}

export interface StudioRenderRequest {
  id: string;
  project_dir: string;
  data_file: string;
  bindings: Record<string, string>;
  parameters: Record<string, string | number | boolean>;
}

export interface StudioSpecTable {
  interface?: string;
  description?: string;
  required?: boolean;
  columns?: InputContractColumn[] | Record<string, { type?: string; description?: string; required?: boolean }>;
}

export interface StudioRenderResponse {
  id?: string;
  code: string;
  language: string;
  bindings_json: Record<string, unknown>;
  spec: {
    id?: string;
    title?: string;
    tier?: number;
    kind?: string;
    language?: string;
    entry?: string;
    dependencies?: string[];
    tables?: Record<string, StudioSpecTable>;
    parameters?: StudioParamSchema[] | Record<string, Omit<StudioParamSchema, 'name'>>;
    [key: string]: unknown;
  };
  parameter_header?: string;
}

export interface StudioDispatchResponse {
  ok: boolean;
  output_dir: string;
  files: string[];
  message?: string;
}

export interface StudioUploadResponse {
  ok: boolean;
  filename: string;
  path: string;
  sniff: StudioSniffResponse;
}

export interface StudioExampleFile {
  name: string;
  path: string;
  sniff: StudioSniffResponse;
}

export interface StudioLoadExampleResponse {
  ok: boolean;
  id: string;
  primary_file: string;
  files: StudioExampleFile[];
  sniff: StudioSniffResponse;
  suggested_bindings: Record<string, string>;
}

export interface StudioRunResponse {
  ok: boolean;
  exit_code: number;
  stdout: string;
  stderr: string;
  run_id?: string;
  output_files: string[];
  preview_url?: string | null;
}

export interface ProjectStepItem {
  title: string;
  templates?: string;
  observation?: string;
  next_branch?: string;
  raw?: string;
}

export interface ProjectRecord {
  id: string;
  title: string;
  path: string;
  meta?: Record<string, unknown>;
  steps?: ProjectStepItem[];
  body: string;
}

export interface ProjectStepRequest {
  title: string;
  templates: string;
  observation: string;
  next_branch: string;
}

export interface InterfaceColumn {
  type: string;
  description: string;
  /** Absent means required, matching the backend and the execution check. */
  required?: boolean;
}

export interface InterfaceMeta {
  type: 'interface';
  slug: string;
  title: string;
  columns: Record<string, InterfaceColumn>;
}

/** Backend-derived template input contract. Bindings map author columns to these internal fields. */
export interface InputContractColumn {
  name: string;
  type: string;
  description: string;
  required: boolean;
}
export interface InputContractTable {
  key: string;
  interface: string;
  description: string;
  required: boolean;
  columns: InputContractColumn[];
}
export interface InputContract {
  bindings: boolean;
  tables: InputContractTable[];
}

export interface TaxonomyCount { value: string; count: number }
export interface TaxonomyDomain extends TaxonomyCount { purposes: TaxonomyCount[] }
export interface DataDomainGroup extends TaxonomyDomain {
  label: string;
}
/** Vocabulary and distinct-page counts come from the backend; the UI holds no second word list. */
export interface MethodTaxonomy {
  total: number;
  domains: TaxonomyDomain[];
  data_domains?: DataDomainGroup[];
  domain_labels?: Record<string, string>;
  purposes: TaxonomyCount[];
  unclassified: { id: string; title: string; path: string }[];
}

export interface MethodHubCard {
  id: string;
  title: string;
  path: string;
  status: Status;
  summary: string;
  data_domains: string[];
  data_domain_labels: string[];
  purposes: string[];
  tags: string[];
  keywords: string[];
  inputs: string[];
  outputs: string[];
  data_contract: { input?: string; output?: string };
  render_bridges: RenderBridge[];
  implementations: MethodImplementation[];
  implementation_status: ImplementationStatus[];
  workflow: Workflow | null;
  next_steps_count: number;
  attached_visualizations: AttachedViz;
  reference_recipes: ReferenceRecipeSummary[];
  unmapped_recipes_count: number;
}

export interface MethodHubsResponse {
  taxonomy: MethodTaxonomy;
  data_domains: DataDomainGroup[];
  methods: MethodHubCard[];
  total: number;
  filtered_total: number;
  unmapped_recipes: ReferenceRecipeSummary[];
  unmapped_recipes_count: number;
}

export interface MethodHubDetail extends MethodHubCard {
  requested_id?: string;
  next?: NextStepsResponse;
}

export interface HubMeta {
  type: 'chart-type' | 'project';
  title: string;
}

export type ItemMeta = LayoutMeta | TemplateMeta | MethodMeta | RecipeMeta;
export type PageMeta = ItemMeta | InterfaceMeta | HubMeta | SourceMeta | ScenarioMeta;

export interface PageSummary<M extends PageMeta = PageMeta> {
  path: string;
  meta: M;
  style_tier?: 'default' | 'variant';
  journal_style?: string;
  /** Explicit outgoing figure links in a method body; general backlinks are not illustrations. */
  figure_refs?: string[];
  relations?: Relation[];
  preview?: Preview | null;
  workflow?: Workflow | null;
  /** Computed by the backend against current code and receipts, never inferred from metadata. */
  implementation_status?: ImplementationStatus[];
  /** Template detail only: the same runtime fact used by lint and the code viewer. */
  runtime?: RuntimeFacts | null;
}

/** Derived remaining action, independent of stored signoff and layout replay state. */
export interface Workflow {
  stage: string;
  queue: 'signoff' | 'confirm' | 'agent' | null;
  label: string;
  reason: string;
  templates: string[];
}

export interface Preview {
  url: string | null;
  /** `stale`: a replay image left from an older code/spec/example, not evidence for the current version. */
  kind: 'replay' | 'stale' | 'source' | 'none' | 'pending';
  label: string;
}

export interface DeletePlan {
  title: string;
  path: string;
  revision: string;
  asset_files: number;
  affected: { path: string; title: string; figure_relations_removed?: number }[];
  figure_relations_removed?: number;
  /** Other layouts' layout.json files that will be rewritten or removed. */
  layout_files_updated?: string[];
  gallery_preserved: boolean;
}

export interface Backlink {
  path: string;
  title: string;
  type: PageType;
}

export interface GalleryMeta {
  status: string;
  version: number;
  data_provenance: string;
  code_provenance: string;
  files: Record<string, string>;
  post: { title: string | null; account: string | null; publish_date: string | null; url: string | null };
  figure: { label: string; caption: string };
}

export interface PageDetail extends PageSummary {
  body: string;
  backlinks: Backlink[];
  gallery: GalleryMeta | null;
  reuse?: { sizing_declared: boolean; mode: string | null; profile: string | null } | null;
  /** Templates only: the internal tables and the explicit binding path. */
  input_contract?: InputContract | null;
}

export interface GraphNode {
  id: string;
  type: PageType;
  title: string;
  /** Effective status (from the shared workflow) once the app has loaded pages. */
  status: Status | null;
  label?: string;
}

/** Interface structure (`feeds`) and reviewed semantic relations remain independent. */
export interface GraphLink {
  source: string;
  target: string;
  kind: 'feeds' | 'link' | 'relation';
  compatibility?: Compatibility;
  verification?: Verification;
  /** False when either end is archived: kept for history, never a current recommendation. */
  active?: boolean;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface LogEntry {
  time: string;
  message: string;
}

/** Source catalog records are discoverable, never executable recommendations. */
export interface CatalogItem {
  id: string; title: string; kind: 'item'; level: 'L0'; status: 'catalog';
  usable: false; run: 'none'; source: string; page: string; use: string;
  summary: string; scenario: string; inputs: string[]; requires: string[];
  chart_types: string[]; tags: string[]; keywords: string[]; license: string;
  language?: string; thumb?: string;
}

export const STATUS_LABEL: Record<Status, string> = {
  pending_signoff: '待签核',
  pending_template: '待模板化',
  draft: '待确认',
  ready: '可用',
  archived: '已归档',
};

export const TYPE_LABEL: Record<PageType, string> = {
  layout: '来源图样',
  template: '绘图模板',
  method: '方法页',
  interface: '数据接口',
  'chart-type': '图型',
  project: '课题',
  recipe: '历史归档模板',
  source: '来源库',
  scenario: '研究场景',
};

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail));
  }
  return res.json();
}

const post = (url: string, body?: unknown) =>
  request<PageDetail>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

const act = (kind: Kind, id: string, action: string) => `/api/${kind}/${encodeURIComponent(id)}/${action}`;

/** Last fetched detail per page, so a page can paint on the first frame of a transition. */
export const pageCache = new Map<string, PageDetail>();
export type VisualDecision = 'pending' | 'kept' | 'removed' | 'later';
export interface CurationItem extends CatalogItem {
  decision: VisualDecision;
  source_id: string;
  images: { url: string; label: string; name: string }[];
  recipes: { id: string; title: string; status: string; page: string }[];
}
export interface CurationInventory { items: CurationItem[]; revision: string }
const previewCache = new Map<string, Preview | null>();
const workflowCache = new Map<string, Workflow | null>();
const previewKey = (meta: PageMeta) =>
  `${meta.type}/${'id' in meta ? meta.id : 'slug' in meta ? meta.slug : meta.title}`;

export function cachePages(pages: PageSummary[]) {
  previewCache.clear();
  workflowCache.clear();
  for (const p of pages) if (p.preview !== undefined) previewCache.set(previewKey(p.meta), p.preview);
  for (const p of pages) if (p.workflow !== undefined) workflowCache.set(previewKey(p.meta), p.workflow);
}

export const api = {
  search: (params: URLSearchParams, signal?: AbortSignal) => request<SearchResponse>(`/api/search?${params}`, {signal}),
  fetchAsset: (id: string) => request<{state?: string; note?: string}>('/api/assets/fetch', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id}),
  }),
  pages: async (light = false, cache = true) => {
    const pages = await request<PageSummary[]>(light ? '/api/pages?light=true' : '/api/pages');
    if (cache) cachePages(pages);
    return pages;
  },
  sourceItems: () => request<CatalogItem[]>('/api/source-items'),
  figureyaCuration: () => request<CurationInventory>('/api/figureya/curation'),
  figureyaDecide: (ids: string[], decision: VisualDecision, revision: string) =>
    request<{ revision: string; decisions: Record<string, VisualDecision> }>('/api/figureya/curation', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids, decision, revision }),
    }),
  page: async (path: string) => {
    const page = await request<PageDetail>(`/api/page?path=${encodeURIComponent(path)}`);
    pageCache.set(path, page);
    if (page.preview !== undefined) previewCache.set(previewKey(page.meta), page.preview);
    if (page.workflow !== undefined) workflowCache.set(previewKey(page.meta), page.workflow);
    return page;
  },
  graph: () => request<GraphData>('/api/graph'),
  methodTaxonomy: () => request<MethodTaxonomy>('/api/method-taxonomy'),
  methodHubs: (params?: { domain?: string; purpose?: string; q?: string }, signal?: AbortSignal) => {
    const qs = new URLSearchParams();
    if (params?.domain) qs.set('domain', params.domain);
    if (params?.purpose) qs.set('purpose', params.purpose);
    if (params?.q) qs.set('q', params.q);
    const suffix = qs.toString();
    return request<MethodHubsResponse>(`/api/method-hubs${suffix ? `?${suffix}` : ''}`, { signal });
  },
  methodHub: (id: string, signal?: AbortSignal) =>
    request<MethodHubDetail>(`/api/methods/${encodeURIComponent(id)}/hub`, { signal }),
  codeFiles: (kind: Kind, id: string, signal?: AbortSignal) => request<CodeListing>(act(kind, id, 'code-files'), { signal }),
  code: (kind: Kind, id: string, variant: CodeVariant, path: string, signal?: AbortSignal) =>
    request<CodeText>(`${act(kind, id, 'code')}?${new URLSearchParams({ variant, path })}`, { signal }),
  log: () => request<LogEntry[]>('/api/log'),
  signoff: (id: string) => post(act('layouts', id, 'signoff')),
  reject: (id: string, reason: string) => post(act('layouts', id, 'reject'), { reason }),
  confirm: (id: string) => post(act('methods', id, 'confirm')),
  /** Author confirmation of a recipe (draft → ready); the backend re-checks the as-is run receipt. */
  confirmRecipe: (id: string) => post(act('recipes', id, 'confirm')),
  /** Author confirmation of a template (draft → ready). */
  confirmTemplate: (id: string) => post(act('templates', id, 'confirm')),
  /** Batch confirm multiple draft templates (draft → ready). */
  batchConfirmTemplates: (ids: string[]) =>
    request<{ confirmed: string[]; count: number }>('/api/templates/batch-confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids, confirmed: true }),
    }),
  returnMethod: (id: string, reason: string) => post(act('methods', id, 'return'), { reason }),
  tags: (kind: Kind, id: string, tags: string[]) => post(act(kind, id, 'tags'), { tags }),
  favorite: (kind: Kind, id: string, value: boolean) => post(act(kind, id, 'favorite'), { value }),
  note: (kind: Kind, id: string, text: string) => post(act(kind, id, 'note'), { text }),
  archive: (kind: Kind, id: string) => post(act(kind, id, 'archive')),
  restore: (kind: Kind, id: string) => post(act(kind, id, 'restore')),
  deletePlan: (kind: Kind, id: string) => request<DeletePlan>(act(kind, id, 'delete-plan')),
  deleteArchived: async (kind: Kind, id: string, revision: string) => {
    const result = await request<DeletePlan & { deleted: boolean; audit: string }>(act(kind, id, 'delete'), {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirmed: true, revision }),
    });
    pageCache.clear();
    return result;
  },
  playbooks: () => request<PlaybooksResponse>('/api/playbooks'),
  nextSteps: (nodeId: string, q = '') =>
    request<NextStepsResponse>(`/api/next/${encodeURIComponent(nodeId)}${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  studioSniff: (path: string) =>
    request<StudioSniffResponse>('/api/studio/sniff', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path }),
    }),
  studioUpload: (filename: string, contentBase64: string, contentText = '') =>
    request<StudioUploadResponse>('/api/studio/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename, content_base64: contentBase64, content_text: contentText }),
    }),
  studioLoadExample: (id: string) =>
    request<StudioLoadExampleResponse>('/api/studio/load-example', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }),
    }),
  studioRenderCode: (payload: StudioRenderRequest, signal?: AbortSignal) =>
    request<StudioRenderResponse>('/api/studio/render-code', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal,
    }),
  studioDispatch: (payload: StudioRenderRequest & { code?: string }) =>
    request<StudioDispatchResponse>('/api/studio/dispatch', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    }),
  studioRun: (payload: StudioRenderRequest & { code?: string }) =>
    request<StudioRunResponse>('/api/studio/run', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    }),
  projects: () => request<ProjectRecord[] | { projects: ProjectRecord[] }>('/api/projects'),
  addProjectStep: (projectId: string, step: ProjectStepRequest) =>
    request<ProjectRecord>(`/api/projects/${encodeURIComponent(projectId)}/step`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(step),
    }),
};

const encodePath = (path: string) => path.split('/').map(encodeURIComponent).join('/');

export const KIND_OF: Record<ItemMeta['type'], Kind> = { layout: 'layouts', template: 'templates', method: 'methods', recipe: 'recipes' };
export const codeDownload = (kind: Kind, id: string, file: Pick<CodeFile, 'variant' | 'path'>) =>
  `${act(kind, id, 'code-download')}?${new URLSearchParams({ variant: file.variant, path: file.path })}`;
export const wikiFile = (path: string) => `/files/wiki/${encodePath(path)}`;
export const galleryFile = (entry: string, file: string) => `/files/gallery/${encodePath(`${entry}/${file}`)}`;
export const pageHref = (path: string) => `#/page/${encodePath(path)}`;
export const studioHref = (id: string) => `#/studio?id=${encodeURIComponent(id)}`;

/** The picture that stands for an item: the gallery thumbnail for a layout, the replay preview for a panel template. */
export function imageOf(meta: PageMeta): string | null {
  const known = previewCache.get(previewKey(meta));
  if (known !== undefined) return known?.url ?? null;
  if (meta.type === 'layout') return wikiFile(`layouts/${meta.id}/thumb.png`);
  if (meta.type === 'template') return wikiFile(`templates/${meta.id}/preview.png`);
  return null;
}

export function previewOf(meta: PageMeta): Preview | null {
  return previewCache.get(previewKey(meta)) ?? null;
}

export function workflowOf(meta: PageMeta): Workflow | null {
  return workflowCache.get(previewKey(meta)) ?? null;
}

export function displayStatus(meta: ItemMeta): string {
  const workflow = workflowOf(meta);
  if (meta.type === 'method') return methodNoteLabel(meta, workflow);
  return workflow?.label ?? STATUS_LABEL[meta.status];
}

/** Author confirmation concerns the knowledge note, independently of algorithm execution. */
export function methodNoteLabel(meta: MethodMeta, workflow?: Workflow | null): string {
  if (meta.status === 'archived') return '已归档';
  if (workflow && workflow.stage !== 'complete' && workflow.label !== '可用') return workflow.label;
  return meta.status === 'ready' ? '笔记已确认' : '笔记待确认';
}

/** Workflow stage → the status colour it stands for; one mapping for badges, graph rings, census and filters. */
const STAGE_STATUS: Record<string, Status> = {
  checking: 'pending_template',
  unknown: 'pending_template',
  archived: 'archived', complete: 'ready', repair_complete: 'ready', signoff: 'pending_signoff',
  template_confirm: 'draft', method_confirm: 'draft',
  template_work: 'pending_template', method_work: 'pending_template',
  layout_work: 'pending_template', template_missing: 'pending_template',
  recipe_confirm: 'draft', recipe_work: 'pending_template',
};

export const stageStatus = (stage: string): Status | undefined => STAGE_STATUS[stage];

/** The derived state of an item; the stored status is history (e.g. a source stays pending_template). */
export function effectiveStatus(meta: ItemMeta, workflow: Workflow | null = workflowOf(meta)): Status {
  return (workflow && STAGE_STATUS[workflow.stage]) ?? meta.status;
}

/** Only web links open from metadata; anything else (javascript:, data:, ...) is shown as text. */
export const safeUrl = (url: string | null | undefined): string | null =>
  url && /^https?:\/\//i.test(url.trim()) ? url.trim() : null;

export const isItem = (meta: PageMeta): meta is ItemMeta =>
  meta.type === 'layout' || meta.type === 'template' || meta.type === 'method' || meta.type === 'recipe';
export const isFigure = (meta: PageMeta): meta is LayoutMeta | TemplateMeta => meta.type === 'layout' || meta.type === 'template';

/** Publish a safe initial listing before independent, expensive graph/evidence requests. */
export async function loadLibrary(observer: {
  pages: (pages: PageSummary[]) => void;
  graph: (graph: GraphData) => void;
  taxonomy: (taxonomy: MethodTaxonomy) => void;
  error?: (message: string) => void;
}, current: () => boolean = () => true, hydrate = true): Promise<void> {
  const publish = (pages: PageSummary[]) => {
    if (!current()) return;
    cachePages(pages);
    observer.pages(pages);
  };
  publish(await api.pages(true, false));
  if (!current() || !hydrate) return;
  await Promise.all([
    api.pages(false, false).then(publish),
    api.graph().then(graph => { if (current()) observer.graph(graph); }),
    api.methodTaxonomy().then(taxonomy => { if (current()) observer.taxonomy(taxonomy); }),
  ].map(promise => promise.catch((error: Error) => { if (current()) observer.error?.(error.message); })));
}
