import { useEffect, useMemo, useState } from 'react';
import { api, CatalogItem, displayStatus, PageSummary, RecipeMeta, safeUrl, SourceMeta, TemplateMeta } from '../api';
import type { AppData } from '../App';
import { pageLink } from '../nav';
import { LicenseBadge } from '../components';
import { matchesFigureQuery } from '../figureModels';
import { matchesRecipeQuery, recipeOrigin } from '../recipes';

export function matchesCatalog(item: CatalogItem, query: string, sourceTitle = ''): boolean {
  const text = [item.id, item.title, item.summary, item.scenario, sourceTitle,
    ...item.keywords, ...item.tags, ...item.chart_types, ...item.inputs, ...item.requires].join(' ').toLowerCase();
  return query.toLowerCase().split(/\s+/).filter(Boolean).every(word => text.includes(word));
}

export function CatalogCards({ items }: { items: CatalogItem[] }) {
  return <div className="source-grid">{items.map(item => {
    const thumb = safeUrl(item.thumb);
    return <article className="source-card" key={item.id}>
      {thumb && <figure><img src={thumb} alt="上游参考图，尚无本库回放" loading="lazy" onError={event => {event.currentTarget.hidden = true;}} /><figcaption>上游参考图 · 非运行证据</figcaption></figure>}
      <p className="small muted">L0 · 目录项 · 未在 Wiki 运行</p>
      <h3>{item.title}</h3><p className="small muted">{item.id}</p>
      <p>{item.summary || item.scenario || '用途见来源说明。'}</p>
      <dl><dt>输入文件</dt><dd>{item.inputs.join('、') || '按模块说明准备'}</dd>
        <dt>依赖</dt><dd>{item.requires.join('、') || '使用前核对模块说明'}</dd></dl>
      <LicenseBadge license={item.license} />
      <p><a {...pageLink(item.page)}>查看来源与使用边界</a></p>
      <code>{item.use.replace(/^wiki\.py/, 'rwiki')}</code>
    </article>;
  })}</div>;
}

export function SourcesView({ data, query = '' }: { data: AppData; query?: string }) {
  const params = new URLSearchParams(query);
  const [source, setSource] = useState(params.get('source') ?? '');
  const [q, setQuery] = useState(params.get('q') ?? '');
  const [items, setItems] = useState<CatalogItem[] | null>(null);
  const [error, setError] = useState('');
  const [limit, setLimit] = useState(24);
  useEffect(() => {
    let active = true;
    api.sourceItems().then(records => {if (active) setItems(records);})
      .catch((failure: Error) => {if (active) setError(failure.message);});
    return () => {active = false;};
  }, []);
  useEffect(() => {
    const current = new URLSearchParams(query);
    setSource(current.get('source') ?? ''); setQuery(current.get('q') ?? ''); setLimit(24);
  }, [query]);
  const sources = data.pages.filter((p): p is PageSummary<SourceMeta> => p.meta.type === 'source');
  const names = new Map(sources.map(p => [p.meta.id, p.meta.title]));
  const shown = useMemo(() => (items ?? []).filter(item => (!source || item.id.split(':')[0] === source)
    && matchesCatalog(item, q, names.get(item.id.split(':')[0]))), [items, source, q, data.pages]);
  const availableRecipes = data.pages.filter((p): p is PageSummary<RecipeMeta> => p.meta.type === 'recipe'
    && p.meta.status !== 'archived' && (!source || p.meta.source?.id === source));
  const recipePaths = new Set(availableRecipes.map(p => p.path.replace(/\.md$/, '')));
  const recipes = availableRecipes.filter(p => matchesRecipeQuery(p.meta, recipeOrigin(p.meta, data.env.titles), q));
  const templates = data.pages.filter((p): p is PageSummary<TemplateMeta> => p.meta.type === 'template'
    && p.meta.status !== 'archived' && (p.meta.sources ?? []).some(s => recipePaths.has(s.replace(/\.md$/, '')))
    && matchesFigureQuery(p.meta, q, data.pages));
  return <section className="sources-view">
    <header className="hero slim"><div className="hero-text"><h1>来源目录</h1>
      <p className="lede">按来源查找可视化模块。L0 仅登记用途、输入与依赖；配方和函数模板保留各自的运行、回放与确认状态。</p></div></header>
    <div className="filters" role="search">
      <a className="button" href="#/figureya">看图筛选 FigureYa</a>
      <input type="search" aria-label="搜索来源模块" placeholder="搜索 FigureYa、图型、模块 ID、输入或依赖" value={q} onChange={e => {setQuery(e.target.value);setLimit(24);}} />
      <select aria-label="来源库" value={source} onChange={e => {setSource(e.target.value);setLimit(24);}}>
        <option value="">全部来源</option>{sources.map(p => <option key={p.meta.id} value={p.meta.id}>{p.meta.title} · {p.meta.id}</option>)}
      </select>
    </div>
    <p className="small">{sources.filter(p => !source || p.meta.id === source).map(p => <span key={p.path}><a {...pageLink(p.path)}>{p.meta.title}</a>{'　'}</span>)}</p>
    <div className="source-assets">
      <details open><summary>L2 · 函数模板（{templates.length}）</summary>
        {templates.map(p => <p key={p.path}><a {...pageLink(p.path)}>{p.meta.title}</a> <span className="muted small">{displayStatus(p.meta)}</span></p>)}
        {!templates.length && <p className="muted">此来源尚无已提炼的函数模板。</p>}
      </details>
      <details><summary>L1 · 整模块配方（{recipes.length}）</summary>
        {recipes.map(p => <p key={p.path}><a {...pageLink(p.path)}>{p.meta.title}</a> <span className="muted small">{displayStatus(p.meta)}</span></p>)}
      </details>
    </div>
    <h2>L0 · 来源目录项{items && `（匹配 ${shown.length} 项）`}</h2>
    <p className="muted small">已升级为配方的同版本条目由 L1 入口代替。上游参考图与现成输出不代表本机运行通过；多语言辅助工具见各来源说明。</p>
    {error ? <p className="notice error" role="alert">来源目录加载失败：{error}</p> : items === null ? <p role="status">正在读取来源目录…</p>
      : <><CatalogCards items={shown.slice(0, limit)} />{!shown.length && <p className="notice">没有符合条件的目录项，试试清空筛选。</p>}
        {shown.length > limit && <button onClick={() => setLimit(n => n + 24)}>继续显示（剩余 {shown.length - limit} 项）</button>}</>}
  </section>;
}
