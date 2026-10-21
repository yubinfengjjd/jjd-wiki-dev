export type Status = 'pending_signoff' | 'pending_template' | 'draft' | 'ready' | 'archived';
export type PageType = 'layout' | 'template' | 'method' | 'interface' | 'chart-type' | 'project';
/** Page types the author acts on; each has its own status machine and the shared favorite/note/tags/archive endpoints. */
export type Kind = 'layouts' | 'templates' | 'methods';

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
}

export interface GraphNode {
  id: string;
  type: PageType;
  title: string;
  status: Status | null;
}

/** `feeds` runs method → interface → template/method and is directed; `link` is any other wiki link. */
export interface GraphLink {
  source: string;
  target: string;
  kind: 'feeds' | 'link';
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
  layout: '整图版式',
  template: '单图模板',
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

export const api = {
  pages: () => request<PageSummary[]>('/api/pages'),
  page: async (path: string) => {
    const page = await request<PageDetail>(`/api/page?path=${encodeURIComponent(path)}`);
    pageCache.set(path, page);
    return page;
  },
  graph: () => request<GraphData>('/api/graph'),
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
};

const encodePath = (path: string) => path.split('/').map(encodeURIComponent).join('/');

export const KIND_OF: Record<ItemMeta['type'], Kind> = { layout: 'layouts', template: 'templates', method: 'methods' };
export const wikiFile = (path: string) => `/files/wiki/${encodePath(path)}`;
export const galleryFile = (entry: string, file: string) => `/files/gallery/${encodePath(`${entry}/${file}`)}`;
export const pageHref = (path: string) => `#/page/${encodePath(path)}`;

/** The picture that stands for an item: the gallery thumbnail for a layout, the replay preview for a panel template. */
export function imageOf(meta: PageMeta): string | null {
  if (meta.type === 'layout') return wikiFile(`layouts/${meta.id}/thumb.png`);
  if (meta.type === 'template') return wikiFile(`templates/${meta.id}/preview.png`);
  return null;
}

export const isItem = (meta: PageMeta): meta is ItemMeta => meta.type === 'layout' || meta.type === 'template' || meta.type === 'method';
export const isFigure = (meta: PageMeta): meta is LayoutMeta | TemplateMeta => meta.type === 'layout' || meta.type === 'template';
