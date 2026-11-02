import { useEffect, useMemo, useRef, useState } from 'react';
import { GraphNode, LayoutMeta, stageStatus, TemplateMeta, TYPE_LABEL, workflowOf } from '../api';
import type { AppData } from '../App';
import { PlateCard } from '../components';
import { Lattice } from '../hero/Lattice';
import { openPage } from '../nav';
import { FigureShelf, galleryEntries, galleryInventory, templateSourceNote, matchesFigureQuery } from '../figureModels';
import { matchesMethodQuery, plottingCodePages } from '../methods';
import { MethodCodeCard } from './MethodCodeCard';

interface Filters {
  q: string;
  tag: string;
  chart: string;
  language: string;
  status: string;
  favorite: boolean;
}

type Shelf = FigureShelf | 'code';
type FigureMeta = LayoutMeta | TemplateMeta;

const EMPTY: Filters = { q: '', tag: '', chart: '', language: '', status: '', favorite: false };
const SHELVES: [Shelf, string][] = [
  ['single', '单 panel 图样'],
  ['template', '可调用模板'],
  ['code', '绘图代码'],
];
// Census and status filter use the backend workflow stage, the same derivation as the queue.
const STAGES: Record<FigureShelf, [string, string][]> = {
  single: [['signoff', '待签核'], ['template_missing', '待补齐模板'], ['template_work', '模板制作中'],
    ['template_confirm', '模板待你确认'], ['layout_work', '待核查版式'], ['complete', '模板已就绪']],
  template: [['template_work', '待完成回放'], ['template_confirm', '待你确认'], ['complete', '可用']],
};

const progressOf = (meta: FigureMeta) => workflowOf(meta)?.stage ?? (meta.status === 'ready' ? 'complete' : meta.status);

function matches(meta: FigureMeta, f: Filters, pages: AppData['pages']): boolean {
  if (f.tag && !meta.tags.includes(f.tag)) return false;
  if (f.chart && !meta.chart_types.includes(f.chart)) return false;
  if (f.language && meta.language !== f.language) return false;
  if (f.status && progressOf(meta) !== f.status) return false;
  if (f.favorite && !meta.favorite) return false;
  if (!f.q) return true;
  return matchesFigureQuery(meta, f.q, pages);
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
  const [shelf, setShelf] = useState<Shelf>('single');
  const inventory = galleryInventory(data.pages, data.env.hiddenSources);

  const entries = useMemo(() => galleryEntries(data.pages), [data.pages]);
  const codePages = plottingCodePages(data.pages);
  const templates = shelf === 'code' ? [] : entries[shelf];
  const stages = shelf === 'code' ? [] : STAGES[shelf];
  const shown = templates.filter((t) => matches(t.meta, f, data.pages));
  const pickShelf = (next: Shelf) => {
    setShelf(next);
    // Status values differ per shelf, so a status filter would silently hide everything.
    setF({ ...EMPTY, q: f.q });
  };
  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => setF({ ...f, [key]: value });

  return (
    <section className="gallery">
      <header className="hero">
        <div className="hero-text">
          <h1>图库</h1>
          <p className="lede">
            按单 panel 图样、可调用模板或绘图代码浏览。依赖原生图和项目自定义函数保留各自入口与验证范围；完整原图仅作溯源。复用时根据实际分组数 n 编排尺寸、标签和间距。
          </p>
          <dl className="census">
            {stages.map(([s, label]) => (
              <div key={s}>
                <dt>
                  <span className={`dot status-${stageStatus(s) ?? s}`} aria-hidden="true" />
                  {label}
                </dt>
                <dd>{templates.filter((t) => progressOf(t.meta) === s).length}</dd>
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
            <span className="muted"> {key === 'code' ? codePages.length : entries[key].length}</span>
          </button>
        ))}
      </div>

      {shelf === 'code' ? <>
        <p className="shelf-help muted small">依赖原生绘图、项目自定义函数和闭包在已有方法页复用，不重复计为单 panel 模板。先核对输入与所选分支收据，再复制到课题运行。</p>
        <div className="filters" role="search"><input type="search" aria-label="搜索绘图代码" placeholder="搜索函数、依赖、来源或关键词" value={f.q} onChange={e => set('q', e.target.value)} /></div>
        <PlottingCodeShelf data={data} query={f.q} />
      </> : <>
      <p className="shelf-help muted small">
        {shelf === 'template' ? '这里按可调用函数浏览；待确认的模板须完成回放和确认后使用。历史模板使用前需由 agent 检查任意 n 的适配情况。' : '这里按单 panel 图形样式浏览，也包含已函数化的图样。同一图样只展示一次；已有函数的图样也可在“可调用模板”中找到。'}
      </p>
      <p className="inventory-note small">当前可浏览 {inventory.styles} 种单 panel 图样、{inventory.templates} 个函数模板。两栏可以包含同一条记录，分别便于看样式和调用代码。{inventory.historical > 0 && `其中 ${inventory.historical} 个历史单 panel 模板也已作为图样展示；它们的整图来源继续归档保留。`}</p>

      <div className="filters" role="search">
        <input
          type="search"
          placeholder="搜索标题、来源、ID、关键词或图型"
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
          {stages.map(([s, label]) => (
            <option key={s} value={s}>{label}</option>
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
            : shelf !== 'template'
              ? '本栏尚无单 panel 图样。确认样式与细节后，用 sci-figure-replica 复刻代表单 panel。'
              : '还没有可调用模板。选定图样签核后，在 agent 里说“处理待办”即可制作。'}
        </p>
      ) : (
        <div className="grid">
          {shown.map((t, i) => (
            <PlateCard key={t.path} path={t.path} meta={t.meta} number={i + 1} sourceLinks={t.sourceLinks} asStyle={shelf === 'single'} note={t.meta.type === 'template' ? templateSourceNote(t.meta, data.pages, data.env.hiddenSources) : undefined} />
          ))}
        </div>
      )}
      </>}
    </section>
  );
}

export function PlottingCodeShelf({ data, query = '' }: { data: AppData; query?: string }) {
  const pages = plottingCodePages(data.pages).filter(p => matchesMethodQuery(p.meta, query));
  return pages.length ? <div className="source-grid">{pages.map(page => <MethodCodeCard key={page.path} page={page} pages={data.pages} />)}</div>
    : <p className="notice">没有匹配的绘图代码。可清空关键词，或到方法库浏览理论、流程与其他代码资料。</p>;
}
