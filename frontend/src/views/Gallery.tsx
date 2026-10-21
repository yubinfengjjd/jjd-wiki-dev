import { useEffect, useMemo, useRef, useState } from 'react';
import { GraphNode, isFigure, LayoutMeta, STATUS_LABEL, Status, TemplateMeta, TYPE_LABEL } from '../api';
import type { AppData } from '../App';
import { PlateCard } from '../components';
import { Lattice } from '../hero/Lattice';
import { openPage } from '../nav';

interface Filters {
  q: string;
  tag: string;
  chart: string;
  language: string;
  status: string;
  favorite: boolean;
}

type Shelf = 'layout' | 'template';
type FigureMeta = LayoutMeta | TemplateMeta;

const EMPTY: Filters = { q: '', tag: '', chart: '', language: '', status: '', favorite: false };
const PIPELINE: Record<Shelf, Status[]> = {
  layout: ['pending_signoff', 'pending_template', 'ready'],
  template: ['draft', 'ready'],
};
const SHELVES: [Shelf, string][] = [
  ['layout', '整图版式'],
  ['template', '单图模板'],
];

function matches(meta: FigureMeta, f: Filters): boolean {
  if (f.tag && !meta.tags.includes(f.tag)) return false;
  if (f.chart && !meta.chart_types.includes(f.chart)) return false;
  if (f.language && meta.language !== f.language) return false;
  if (f.status && meta.status !== f.status) return false;
  if (f.favorite && !meta.favorite) return false;
  if (!f.q) return true;
  const haystack = [meta.title, ...meta.tags, ...meta.chart_types]
    .join(' ')
    .toLowerCase();
  return f.q.toLowerCase().split(/\s+/).every((word) => haystack.includes(word));
}

const uniq = (values: string[]) => [...new Set(values)].sort();

function LatticeFigure({ data }: { data: AppData }) {
  const host = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<GraphNode | null>(null);

  useEffect(() => {
    const lattice = new Lattice(host.current!, data.graph, (id) => openPage(id), setHover);
    return () => lattice.dispose();
  }, [data.graph]);

  return (
    <figure className="lattice">
      <div className="lattice-stage" ref={host} />
      <figcaption>
        {hover ? (
          <>
            <b>{TYPE_LABEL[hover.type]}</b> {hover.title}
          </>
        ) : (
          <>
            <b>知识晶格</b> 每个点是一页 wiki，弧线是页面之间的链接。拖动旋转，点一个点打开它。
          </>
        )}
      </figcaption>
    </figure>
  );
}

export function Gallery({ data }: { data: AppData }) {
  const [f, setF] = useState<Filters>(EMPTY);
  const [shelf, setShelf] = useState<Shelf>('layout');

  const figures = useMemo(
    () =>
      data.pages.flatMap((p) =>
        isFigure(p.meta) && p.meta.status !== 'archived' ? [{ path: p.path, meta: p.meta }] : [],
      ),
    [data.pages],
  );
  const templates = figures.filter((t) => t.meta.type === shelf);
  const shown = templates.filter((t) => matches(t.meta, f));
  const pickShelf = (next: Shelf) => {
    setShelf(next);
    // Status values differ per shelf, so a status filter would silently hide everything.
    setF({ ...f, status: '' });
  };
  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => setF({ ...f, [key]: value });

  return (
    <section className="gallery">
      <header className="hero">
        <div className="hero-text">
          <h1>图库</h1>
          <p className="lede">
            复刻并签核过的科研数据图。整张图签核后拆成单图模板，agent 读模板的适用说明、按你的数据挑出合适的几张，换上你的数据重新出图；需要先做分析的，到方法库找能接上的方法。标签只帮助搜索，不限定用途。
          </p>
          <dl className="census">
            {PIPELINE[shelf].map((s) => (
              <div key={s}>
                <dt>
                  <span className={`dot status-${s}`} aria-hidden="true" />
                  {STATUS_LABEL[s]}
                </dt>
                <dd>{templates.filter((t) => t.meta.status === s).length}</dd>
              </div>
            ))}
          </dl>
        </div>
        <LatticeFigure data={data} />
      </header>

      <div className="tabs shelf" role="tablist" aria-label="图库分栏">
        {SHELVES.map(([key, label]) => (
          <button key={key} role="tab" aria-selected={shelf === key} className={shelf === key ? 'active' : ''} onClick={() => pickShelf(key)}>
            {label}
            <span className="muted"> {figures.filter((t) => t.meta.type === key).length}</span>
          </button>
        ))}
      </div>

      <div className="filters" role="search">
        <input
          type="search"
          placeholder="搜索标题、标签、图型"
          aria-label="搜索"
          value={f.q}
          onChange={(e) => set('q', e.target.value)}
        />
        <select aria-label="标签" value={f.tag} onChange={(e) => set('tag', e.target.value)}>
          <option value="">全部标签</option>
          {uniq(templates.flatMap((t) => t.meta.tags)).map((tag) => (
            <option key={tag} value={tag}>{tag}</option>
          ))}
        </select>
        <select aria-label="图型" value={f.chart} onChange={(e) => set('chart', e.target.value)}>
          <option value="">全部图型</option>
          {uniq(templates.flatMap((t) => t.meta.chart_types)).map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <select aria-label="语言" value={f.language} onChange={(e) => set('language', e.target.value)}>
          <option value="">全部语言</option>
          {uniq(templates.map((t) => t.meta.language)).map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
        <select aria-label="状态" value={f.status} onChange={(e) => set('status', e.target.value)}>
          <option value="">全部状态</option>
          {PIPELINE[shelf].map((s) => (
            <option key={s} value={s}>{STATUS_LABEL[s]}</option>
          ))}
        </select>
        <label className="check">
          <input type="checkbox" checked={f.favorite} onChange={(e) => set('favorite', e.target.checked)} />
          只看收藏
        </label>
      </div>

      {shown.length === 0 ? (
        <p className="notice">
          {templates.length > 0
            ? '没有符合筛选条件的图，换个关键词或清空筛选再试。'
            : shelf === 'layout'
              ? '还没有收录任何图。用 sci-figure-replica 复刻一张图，它会自动出现在这里。'
              : '还没有单图模板。整图签核后，在 agent 里说“处理待办”即可拆出。'}
        </p>
      ) : (
        <div className="grid">
          {shown.map((t, i) => (
            <PlateCard key={t.path} path={t.path} meta={t.meta} number={i + 1} />
          ))}
        </div>
      )}
    </section>
  );
}
