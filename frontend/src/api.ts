export type Status = 'pending_signoff' | 'pending_template' | 'draft' | 'ready' | 'archived';
export type PageType = 'layout' | 'template' | 'method' | 'interface' | 'chart-type' | 'project';
/** Page types the author acts on; each has its own status machine and the shared favorite/note/tags/archive endpoints. */
export type Kind = 'layouts' | 'templates' | 'methods';

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
export interface CodeFile {
  variant: CodeVariant;
  path: string;
  language: string;
  size: number;
  sha256: string;
  text: boolean;
  source: unknown;
  verification: Verification;
}
export interface CodeListing { files: CodeFile[]; note: string }
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
  layouts: string[];
  panels: string[];
  chart_types: string[];
}

export interface MethodMeta extends ItemBase {
  type: 'method';
  /** Interface slugs the analysis reads and the tables it is finally shaped into. */
  inputs: string[];
  outputs: string[];
  source:
    | { kind: 'post'; gallery_entry: string }
    | { kind: 'project'; path: string }
    | { kind: 'repo'; url: string; commit: string }
    | { kind: 'written' };
  license: string;
  cite: string[];
}

export interface InterfaceMeta {
  type: 'interface';
  slug: string;
  title: string;
  columns: Record<string, { type: string; description: string }>;
}

export interface HubMeta {
  type: 'chart-type' | 'project';
  title: string;
}

export type ItemMeta = LayoutMeta | TemplateMeta | MethodMeta;
export type PageMeta = ItemMeta | InterfaceMeta | HubMeta;

export interface PageSummary<M extends PageMeta = PageMeta> {
  path: string;
  meta: M;
  /** Explicit outgoing figure links in a method body; general backlinks are not illustrations. */
  figure_refs?: string[];
  relations?: Relation[];
  preview?: Preview | null;
  workflow?: Workflow | null;
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
  kind: 'replay' | 'source' | 'none';
  label: string;
}

export interface DeletePlan {
  title: string;
  path: string;
  revision: string;
  asset_files: number;
  affected: { path: string; title: string }[];
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
}

export interface GraphNode {
  id: string;
  type: PageType;
  title: string;
  status: Status | null;
}

/** Interface structure (`feeds`) and reviewed semantic relations remain independent. */
export interface GraphLink {
  source: string;
  target: string;
  kind: 'feeds' | 'link' | 'relation';
  compatibility?: Compatibility;
  verification?: Verification;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface LogEntry {
  time: string;
  message: string;
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
  template: '可调用模板',
  method: '分析方法',
  interface: '数据接口',
  'chart-type': '图型',
  project: '课题',
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
const previewCache = new Map<string, Preview | null>();
const workflowCache = new Map<string, Workflow | null>();
const previewKey = (meta: PageMeta) => 'id' in meta ? `${meta.type}/${meta.id}` : '';

export const api = {
  pages: async () => {
    const pages = await request<PageSummary[]>('/api/pages');
    previewCache.clear();
    workflowCache.clear();
    for (const p of pages) if (p.preview !== undefined) previewCache.set(previewKey(p.meta), p.preview);
    for (const p of pages) if (p.workflow !== undefined) workflowCache.set(previewKey(p.meta), p.workflow);
    return pages;
  },
  page: async (path: string) => {
    const page = await request<PageDetail>(`/api/page?path=${encodeURIComponent(path)}`);
    pageCache.set(path, page);
    if (page.preview !== undefined) previewCache.set(previewKey(page.meta), page.preview);
    if (page.workflow !== undefined) workflowCache.set(previewKey(page.meta), page.workflow);
    return page;
  },
  graph: () => request<GraphData>('/api/graph'),
  codeFiles: (kind: Kind, id: string, signal?: AbortSignal) => request<CodeListing>(act(kind, id, 'code-files'), { signal }),
  code: (kind: Kind, id: string, variant: CodeVariant, path: string, signal?: AbortSignal) =>
    request<CodeText>(`${act(kind, id, 'code')}?${new URLSearchParams({ variant, path })}`, { signal }),
  log: () => request<LogEntry[]>('/api/log'),
  signoff: (id: string) => post(act('layouts', id, 'signoff')),
  reject: (id: string, reason: string) => post(act('layouts', id, 'reject'), { reason }),
  confirm: (id: string) => post(act('methods', id, 'confirm')),
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
};

const encodePath = (path: string) => path.split('/').map(encodeURIComponent).join('/');

export const KIND_OF: Record<ItemMeta['type'], Kind> = { layout: 'layouts', template: 'templates', method: 'methods' };
export const codeDownload = (kind: Kind, id: string, file: Pick<CodeFile, 'variant' | 'path'>) =>
  `${act(kind, id, 'code-download')}?${new URLSearchParams({ variant: file.variant, path: file.path })}`;
export const wikiFile = (path: string) => `/files/wiki/${encodePath(path)}`;
export const galleryFile = (entry: string, file: string) => `/files/gallery/${encodePath(`${entry}/${file}`)}`;
export const pageHref = (path: string) => `#/page/${encodePath(path)}`;

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
  return workflowOf(meta)?.label ?? STATUS_LABEL[meta.status];
}

export const isItem = (meta: PageMeta): meta is ItemMeta => meta.type === 'layout' || meta.type === 'template' || meta.type === 'method';
export const isFigure = (meta: PageMeta): meta is LayoutMeta | TemplateMeta => meta.type === 'layout' || meta.type === 'template';
