import { FormEvent, useEffect, useMemo, useState } from 'react';
import {
  HubMeta,
  InterfaceMeta,
  MethodMeta,
  PageSummary,
  RecipeMeta,
  ScenarioMeta,
  SourceMeta,
  TemplateMeta,
} from '../api';
import type { AppData } from '../App';
import { TypeMark } from '../components';
import { galleryInventory } from '../figureModels';
import { matchesMethodQuery } from '../methods';
import { pageLink } from '../nav';
import { MethodCodeCard } from './MethodCodeCard';
import { SearchView } from './SearchView';

export type ResourceTab =
  | 'technical'
  | 'workflow'
  | 'interfaces'
  | 'chart-types'
  | 'gallery'
  | 'sources'
  | 'search';

function parseTab(query = ''): ResourceTab {
  const raw = new URLSearchParams(query.replace(/^\?/, '')).get('tab') ?? '';
  if (
    raw === 'technical' ||
    raw === 'workflow' ||
    raw === 'interfaces' ||
    raw === 'chart-types' ||
    raw === 'gallery' ||
    raw === 'sources' ||
    raw === 'search'
  ) {
    return raw;
  }
  return 'technical';
}

export function ResourcesView({ data, query = '' }: { data: AppData; query?: string }) {
  const [tab, setTab] = useState<ResourceTab>(() => parseTab(query));
  const [filterText, setFilterText] = useState('');
  const [globalQuery, setGlobalQuery] = useState('');

  useEffect(() => {
    setTab(parseTab(query));
    setFilterText('');
  }, [query]);

  const selectTab = (next: ResourceTab) => {
    setTab(next);
    setFilterText('');
    if (typeof location !== 'undefined') {
      location.hash = next === 'technical' ? '#/resources' : `#/resources?tab=${next}`;
    }
  };

  const technicalPages = useMemo(
    () =>
      data.pages.filter(
        (p): p is PageSummary<MethodMeta> =>
          p.meta.type === 'method' && p.meta.method_kind === 'technical' && p.meta.status !== 'archived',
      ),
    [data.pages],
  );
  const workflowPages = useMemo(
    () =>
      data.pages.filter(
        (p): p is PageSummary<MethodMeta> =>
          p.meta.type === 'method' && p.meta.method_kind === 'workflow' && p.meta.status !== 'archived',
      ),
    [data.pages],
  );
  const interfacePages = useMemo(
    () =>
      data.pages
        .filter((p): p is PageSummary<InterfaceMeta> => p.meta.type === 'interface')
        .sort((a, b) => a.meta.slug.localeCompare(b.meta.slug)),
    [data.pages],
  );
  const chartTypePages = useMemo(
    () =>
      data.pages
        .filter((p): p is PageSummary<HubMeta> => p.meta.type === 'chart-type')
        .sort((a, b) => a.meta.title.localeCompare(b.meta.title)),
    [data.pages],
  );
  const sourcePages = useMemo(
    () => data.pages.filter((p): p is PageSummary<SourceMeta> => p.meta.type === 'source'),
    [data.pages],
  );
  const recipePages = useMemo(
    () => data.pages.filter((p): p is PageSummary<RecipeMeta> => p.meta.type === 'recipe' && p.meta.status !== 'archived'),
    [data.pages],
  );
  const scenarioPages = useMemo(
    () => data.pages.filter((p): p is PageSummary<ScenarioMeta> => p.meta.type === 'scenario'),
    [data.pages],
  );
  const templates = useMemo(
    () => data.pages.filter((p): p is PageSummary<TemplateMeta> => p.meta.type === 'template' && p.meta.status !== 'archived'),
    [data.pages],
  );
  const inventory = useMemo(() => galleryInventory(data.pages, data.env.hiddenSources), [data.pages, data.env.hiddenSources]);

  const qLower = filterText.trim().toLowerCase();
  const filteredTechnical = technicalPages.filter((p) => !qLower || matchesMethodQuery(p.meta, filterText));
  const filteredWorkflow = workflowPages.filter((p) => !qLower || matchesMethodQuery(p.meta, filterText));
  const filteredInterfaces = interfacePages.filter(
    (p) =>
      !qLower ||
      `${p.meta.slug} ${p.meta.title} ${Object.keys(p.meta.columns).join(' ')}`.toLowerCase().includes(qLower),
  );
  const filteredChartTypes = chartTypePages.filter((p) => !qLower || `${p.path} ${p.meta.title}`.toLowerCase().includes(qLower));

  const tabs: [ResourceTab, string, number | null][] = [
    ['technical', '技术与适配代码', technicalPages.length],
    ['workflow', '组合流程', workflowPages.length],
    ['interfaces', '数据接口契约', interfacePages.length],
    ['chart-types', '图型百科', chartTypePages.length],
    ['gallery', '完整图库索引', inventory.templates],
    ['sources', '来源与 FigureYa 归档', sourcePages.length + recipePages.length],
    ['search', '全库搜索', null],
  ];

  const handleGlobalSearch = (event: FormEvent) => {
    event.preventDefault();
    const cleaned = globalQuery.trim();
    location.hash = cleaned ? `#/search?q=${encodeURIComponent(cleaned)}` : '#/search';
  };

  return (
    <section className="resources-hub">
      <header className="gallery-top-bar">
        <div className="gallery-title-group">
          <span className="studio-eyebrow">RESOURCES · CONTRACTS · CATALOGS</span>
          <h1>资料与检索中心</h1>
          <p className="muted small">
            集中查阅技术适配代码、组合流程资料、标准数据接口契约、图型百科、完整图库索引以及 FigureYa 上游来源归档。
          </p>
        </div>
        <form className="resources-quick-search" onSubmit={handleGlobalSearch} role="search">
          <input
            type="search"
            value={globalQuery}
            onChange={(e) => setGlobalQuery(e.target.value)}
            placeholder="全库正文与来源搜索…"
            aria-label="全库搜索跳转"
          />
          <button type="submit" className="primary small">全库搜索</button>
          <a className="button small" href="#/search">高级搜索</a>
        </form>
      </header>

      <nav className="resources-tabs sheet" role="tablist" aria-label="资料分类标签">
        {tabs.map(([id, label, count]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            className={tab === id ? 'resource-tab active' : 'resource-tab'}
            onClick={() => selectTab(id)}
          >
            <span>{label}</span>
            {count !== null && <span className="pill-count">{count}</span>}
          </button>
        ))}
      </nav>

      {tab !== 'search' && tab !== 'gallery' && tab !== 'sources' && (
        <div className="resources-filter-bar">
          <input
            type="search"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            placeholder="按名称、slug 或关键词过滤当前列表…"
            aria-label="过滤资料列表"
          />
        </div>
      )}

      {tab === 'technical' && (
        <section aria-label="技术与适配代码">
          <p className="muted small">保留资料分类、语言与逐分支验证范围；同一实现的多份项目副本不计为独立分析方法。</p>
          {filteredTechnical.length === 0 ? (
            <p className="notice">没有匹配的技术资料条目。</p>
          ) : (
            <div className="source-grid">
              {filteredTechnical.map((page) => <MethodCodeCard key={page.path} page={page} pages={data.pages} />)}
            </div>
          )}
        </section>
      )}

      {tab === 'workflow' && (
        <section aria-label="组合流程资料">
          <p className="muted small">端到端组合流程参考资料；不作为单个可执行分析节点重复计数。</p>
          {filteredWorkflow.length === 0 ? (
            <p className="notice">没有匹配的组合流程资料。</p>
          ) : (
            <div className="source-grid">
              {filteredWorkflow.map((page) => <MethodCodeCard key={page.path} page={page} pages={data.pages} />)}
            </div>
          )}
        </section>
      )}

      {tab === 'interfaces' && (
        <section aria-label="数据接口契约">
          <p className="muted small">
            共 {interfacePages.length} 个标准数据接口。外部数据不必改名为 <code>&lt;接口&gt;.csv</code>，可通过 <code>render --bindings</code> 显式映射列名。
          </p>
          <div className="interface-catalog-grid">
            {filteredInterfaces.map((p) => {
              const cols = Object.entries(p.meta.columns);
              const producers = data.flow.inputs(p.path);
              const consumers = data.flow.outputs(p.path);
              return (
                <article key={p.path} className="sheet interface-card">
                  <div className="interface-card-head">
                    <TypeMark type="interface" />
                    <h3><a {...pageLink(p.path)}>{p.meta.title}</a></h3>
                    <code>{p.meta.slug}.csv</code>
                  </div>
                  <p className="small muted">
                    字段 {cols.length} 列 · 产出 {producers.length} 个方法 · 消费 {consumers.length} 个下游
                  </p>
                  <div className="interface-col-chips">
                    {cols.slice(0, 6).map(([name, col]) => (
                      <span key={name} className="sniff-chip" title={col.description}>
                        <code>{name}</code>
                        <small>{col.required === false ? '可选' : '必需'}</small>
                      </span>
                    ))}
                    {cols.length > 6 && <span className="small muted">+{cols.length - 6} 列</span>}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      )}

      {tab === 'chart-types' && (
        <section aria-label="图型百科">
          <div className="chart-type-grid">
            {filteredChartTypes.map((p) => {
              const slug = p.path.replace(/^chart-types\/|\.md$/g, '');
              const count = templates.filter((t) => t.meta.chart_types.includes(slug)).length;
              return (
                <article key={p.path} className="sheet chart-type-card">
                  <TypeMark type="chart-type" />
                  <h3><a {...pageLink(p.path)}>{p.meta.title}</a></h3>
                  <p className="small muted"><code>{slug}</code> · {count} 个关联模板</p>
                </article>
              );
            })}
            {filteredChartTypes.length === 0 && (
              <p className="notice">暂无图型百科条目。</p>
            )}
          </div>
        </section>
      )}

      {tab === 'gallery' && (
        <section className="sheet resources-gallery-index" aria-label="完整图库索引">
          <h2>生物信息可视化完整图库索引</h2>
          <p className="small muted">
            当前收录 <strong>{inventory.templates}</strong> 个可调用函数模板、<strong>{inventory.styles}</strong> 种图样、
            <strong>{inventory.sources}</strong> 个单 panel 图样来源。
          </p>
          <div className="resources-entry-actions">
            <a className="button primary" href="#/gallery">进入完整可视化图库 (#/gallery)</a>
            <a className="button" href="#/studio">打开独立作图工作台 (#/studio)</a>
          </div>
          <div className="resources-template-mini-list">
            {templates.slice(0, 24).map((t) => (
              <a key={t.path} className="object-pill" {...pageLink(t.path)}>
                <code>{t.meta.id}</code>
                <span>{t.meta.title}</span>
              </a>
            ))}
          </div>
        </section>
      )}

      {tab === 'sources' && (
        <section className="resources-sources-panel" aria-label="来源与 FigureYa 归档">
          <div className="resources-entry-cards">
            <article className="sheet resources-entry-card">
              <h3>上游来源库与 L0 目录 ({sourcePages.length})</h3>
              <p className="small muted">查阅上游开源项目授权协议、引用信息与原始目录项。</p>
              <a className="button primary small" href="#/sources">打开来源目录 (#/sources)</a>
            </article>
            <article className="sheet resources-entry-card">
              <h3>历史归档模板与源码（{recipePages.length}）</h3>
              <p className="small muted">保留只读历史 R/Python 模块参考运行收据与许可标记，新模板统一归入绘图模板库。</p>
              <a className="button primary small" href="#/recipes">打开历史归档模板 (#/recipes)</a>
            </article>
            <article className="sheet resources-entry-card">
              <h3>FigureYa 看图筛选与归档</h3>
              <p className="small muted">逐图审阅 FigureYa 上游原图并管理入库筛选状态。</p>
              <a className="button small" href="#/figureya">打开 FigureYa 筛选 (#/figureya)</a>
            </article>
            <article className="sheet resources-entry-card">
              <h3>研究场景 ({scenarioPages.length}) & 操作日志</h3>
              <p className="small muted">按研究场景索引与 Git 审计记录浏览知识库变更。</p>
              <div className="resources-entry-actions">
                <a className="button small" href="#/scenarios">研究场景 (#/scenarios)</a>
                <a className="button small" href="#/log">变更日志 (#/log)</a>
              </div>
            </article>
          </div>
        </section>
      )}

      {tab === 'search' && (
        <section aria-label="嵌入式全库搜索">
          <SearchView query={query} />
        </section>
      )}
    </section>
  );
}
