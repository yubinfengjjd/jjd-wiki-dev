import { useEffect, useMemo, useRef, useState } from 'react';
import {
  api,
  DataDomainGroup,
  InterfaceMeta,
  isItem,
  MethodHubCard,
  MethodHubsResponse,
  MethodMeta,
  PageSummary,
  ReferenceRecipeSummary,
  studioHref,
} from '../api';
import type { AppData } from '../App';
import { LicenseBadge, TypeMark } from '../components';
import { pageLink } from '../nav';
import {
  buildFallbackMethodHub,
  CANONICAL_DATA_DOMAINS,
  dataDomainGroups,
  domainLabel,
  domainsForMeta,
  filterAnalysisMethods,
  matchesMethodQuery,
  methodBrowseKind,
  methodSelectionHref,
  normalizeMethodSelection,
  parseMethodQuery,
  purposeOptionsFor,
  verifiedImplementations,
} from '../methods';
import { MethodCodeCard } from './MethodCodeCard';

function previewSourceBadge(item: MethodHubCard['attached_visualizations']['all_previews'][number], curatedItem?: MethodHubCard['attached_visualizations']['curated'][number]): string {
  const readySuffix = curatedItem?.status === 'ready' ? ' · 图模板可用' : '';
  if (item.source === 'render_bridged') return '经抽取表转换';
  if (item.source === 'object_compatible') return item.match_type === 'partial' ? '部分对象匹配' : '对象直连兼容';
  if (item.compatibility === 'adaptable') return `需要适配${readySuffix}`;
  if (item.compatibility === 'direct') return `直接兼容${readySuffix || ' · 图模板可用'}`;
  if (item.compatibility === 'unreviewed') return '主归属 · 待审查';
  return `语义关联${readySuffix}`;
}

function HubMethodCard({ hub, taxonomy }: { hub: MethodHubCard; taxonomy: AppData['taxonomy'] }) {
  const verifiedCount = verifiedImplementations(
    { implementations: hub.implementations } as MethodMeta,
    hub.implementation_status,
  ).length;
  const totalImpls = hub.implementations.length;
  const previews = hub.attached_visualizations.all_previews.slice(0, 4);
  const recipeSlots = Math.max(0, 4 - previews.length);
  const previewRecipes = recipeSlots > 0 ? hub.reference_recipes.slice(0, recipeSlots) : [];
  const curatedById = new Map(hub.attached_visualizations.curated.map((c) => [c.id, c]));
  const totalVizCount = new Set([
    ...hub.attached_visualizations.curated.map((v) => v.id),
    ...hub.attached_visualizations.object_compatible.map((v) => v.id),
    ...hub.attached_visualizations.render_bridged.map((v) => v.id),
  ]).size;

  return (
    <article className="sheet method-hub-card">
      <div className="method-hub-head">
        <div className="method-hub-badges">
          {hub.data_domains.map((slug, idx) => (
            <span key={slug} className="domain-pill">
              {hub.data_domain_labels[idx] || domainLabel(slug, taxonomy)}
            </span>
          ))}
          {hub.purposes.map((purpose) => (
            <span key={purpose} className="purpose-pill">{purpose}</span>
          ))}
        </div>
        <span className={`impl-status-pill ${verifiedCount > 0 ? 'verified' : 'unverified'}`}>
          {verifiedCount > 0
            ? `已验证 ${verifiedCount}/${totalImpls} 个实现`
            : '理论与模板就绪 · 暂无已验证实现'}
        </span>
      </div>

      <h3 className="method-hub-title">
        <a {...pageLink(hub.path)}>{hub.title}</a>
      </h3>
      <p className="method-hub-summary small">{hub.summary || '分析理论与下游出图入口。'}</p>

      <div className="method-object-flow" aria-label="输入与输出对象契约">
        <div className="object-flow-side">
          <span className="object-flow-label">输入</span>
          {hub.inputs.length > 0 ? (
            <div className="object-pill-row">
              {hub.inputs.map((slug) => (
                <a key={slug} className="object-pill" {...pageLink(`interfaces/${slug}.md`)}>
                  <code>{slug}</code>
                </a>
              ))}
            </div>
          ) : (
            <span className="object-pill text-only">{hub.data_contract?.input || '上游分析对象 / 表达矩阵'}</span>
          )}
        </div>
        <span className="object-flow-arrow" aria-hidden="true">→</span>
        <div className="object-flow-side">
          <span className="object-flow-label">输出</span>
          {hub.outputs.length > 0 ? (
            <div className="object-pill-row">
              {hub.outputs.map((slug) => (
                <a key={slug} className="object-pill out" {...pageLink(`interfaces/${slug}.md`)}>
                  <code>{slug}</code>
                </a>
              ))}
            </div>
          ) : (
            <span className="object-pill out text-only">{hub.data_contract?.output || '结构化分析结果表'}</span>
          )}
        </div>
      </div>

      <div className="method-viz-strip" aria-label="配套可视化模板预览">
        <div className="viz-strip-head">
          <span className="small muted">配套出图模板（{totalVizCount}）</span>
          {hub.render_bridges.length > 0 && (
            <span className="bridge-mini-note">含 {hub.render_bridges.length} 条抽取表转换</span>
          )}
        </div>
        {(previews.length > 0 || previewRecipes.length > 0) ? (
          <div className="viz-strip-thumbs">
            {previews.map((viz) => {
              const curatedItem = curatedById.get(viz.id);
              const badge = previewSourceBadge(viz, curatedItem);
              return (
                <a
                  key={viz.id}
                  className="viz-thumb-tile"
                  {...pageLink(viz.path)}
                  title={`${viz.title} (${viz.id}) · ${badge}`}
                >
                  <div className="viz-thumb-img">
                    {viz.preview_url ? (
                      <img src={viz.preview_url} alt={viz.title} loading="lazy" />
                    ) : (
                      <span className="viz-thumb-empty">{viz.chart_types[0] || viz.language || '模板'}</span>
                    )}
                  </div>
                  <div className="viz-thumb-meta">
                    <code className="viz-slug">{viz.id}</code>
                    <span className="viz-compat-label">{badge}</span>
                  </div>
                </a>
              );
            })}
            {previewRecipes.map((rec) => (
              <a
                key={`ref-${rec.id}`}
                className="viz-thumb-tile viz-thumb-recipe"
                {...pageLink(rec.path)}
                title={`${rec.title} (${rec.id}) · L1 FigureYa 源码参考`}
              >
                <div className="viz-thumb-img">
                  {rec.preview_url ? (
                    <img src={rec.preview_url} alt={rec.title} loading="lazy" />
                  ) : (
                    <span className="viz-thumb-empty">{rec.chart_types[0] || 'L1 配方'}</span>
                  )}
                </div>
                <div className="viz-thumb-meta">
                  <code className="viz-slug">{rec.id}</code>
                  <span className="viz-compat-label viz-badge-l1">L1 源码参考</span>
                </div>
              </a>
            ))}
          </div>
        ) : (
          <p className="viz-strip-empty small muted">暂无挂载可视化模板；可进入查看理论说明与下游分支。</p>
        )}
      </div>

      <footer className="method-hub-foot">
        <div className="method-hub-stats small muted">
          <span>{hub.next_steps_count} 个下游方向</span>
          <span>·</span>
          {hub.reference_recipes.length > 0 ? (
            <a className="method-recipe-count-link" href={`#/recipes?method=${encodeURIComponent(hub.id)}`}>
              {hub.reference_recipes.length} 个 FigureYa 参考 →
            </a>
          ) : (
            <span>0 个参考配方</span>
          )}
        </div>
        <a className="button primary small" {...pageLink(hub.path)}>
          进入方法与出图
        </a>
      </footer>
    </article>
  );
}

export function methodHubsQueryKey(selection: { domain: string; purpose: string; q: string }): string {
  return JSON.stringify([selection.domain, selection.purpose, selection.q.trim()]);
}

export function selectMatchingHubs(
  hubsState: { key: string; data: MethodHubsResponse } | null,
  currentKey: string,
  searchText: string,
  selectionQ: string,
): MethodHubsResponse | null {
  if (!hubsState || hubsState.key !== currentKey) return null;
  if (searchText.trim() !== selectionQ.trim()) return null;
  return hubsState.data;
}

export function resolveRecipeLicense(
  rec: Pick<ReferenceRecipeSummary, 'path' | 'license'>,
  pages: PageSummary[],
): string | undefined {
  if (rec.license) return rec.license;
  const page = pages.find((p) => p.path === rec.path);
  const meta = page?.meta as { license?: string } | undefined;
  return meta?.license;
}

function UnmappedRecipesSection({ recipes, pages }: { recipes: ReferenceRecipeSummary[]; pages: PageSummary[] }) {
  if (!recipes.length) {
    return <p className="notice">当前所有参考配方均已映射到至少一个分析方法。</p>;
  }
  return (
    <div className="unmapped-recipes-grid">
      {recipes.map((rec) => {
        const license = resolveRecipeLicense(rec, pages);
        return (
          <article key={rec.id} className="sheet unmapped-recipe-card">
            <div className="unmapped-recipe-thumb">
              {rec.preview_url ? (
                <img src={rec.preview_url} alt={rec.title} loading="lazy" />
              ) : (
                <span className="muted small">暂无运行图</span>
              )}
            </div>
            <div className="unmapped-recipe-body">
              <div className="unmapped-recipe-top">
                <h3><a {...pageLink(rec.path)}>{rec.title}</a></h3>
                <span className="badge">未绑定单一方法</span>
              </div>
              <p className="small muted"><code>{rec.id}</code> · {rec.language.toUpperCase() || 'R'}</p>
              {rec.note && <p className="small">{rec.note}</p>}
              <div className="unmapped-recipe-actions">
                {license && <LicenseBadge license={license} />}
                <a className="button small" {...pageLink(rec.path)}>配方详情</a>
                <a className="button primary small" href={studioHref(rec.id)}>打开工作台</a>
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}

export function MethodsView({ data, query = '' }: { data: AppData; query?: string }) {
  const byPath = new Map(data.pages.map((p) => [p.path, p]));
  const params = new URLSearchParams(query.replace(/^\?/, ''));
  const viewTab = params.get('tab') ?? '';
  const kind = methodBrowseKind(query);
  const interfaces = data.pages.filter((p): p is PageSummary<InterfaceMeta> => p.meta.type === 'interface');

  const [hubsState, setHubsState] = useState<{ key: string; data: MethodHubsResponse } | null>(null);
  const [hubsError, setHubsError] = useState('');
  const abortRef = useRef<AbortController | null>(null);

  const rawSelection = parseMethodQuery(query);
  const rawKey = methodHubsQueryKey(rawSelection);
  const initialTaxonomy = (hubsState?.key === rawKey ? hubsState.data.taxonomy : undefined) ?? data.taxonomy;
  const selection = normalizeMethodSelection(rawSelection, initialTaxonomy);
  const currentKey = methodHubsQueryKey(selection);
  const [search, setSearch] = useState(selection.q);
  useEffect(() => { setSearch(selection.q); }, [selection.q]);

  useEffect(() => {
    if (typeof fetch !== 'function') return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const reqKey = currentKey;
    setHubsError('');
    api.methodHubs({ domain: selection.domain, purpose: selection.purpose, q: selection.q }, ctrl.signal)
      .then((res) => {
        if (!ctrl.signal.aborted && res && Array.isArray(res.methods)) {
          setHubsState({ key: reqKey, data: res });
        }
      })
      .catch((err: Error) => {
        if (!ctrl.signal.aborted) {
          setHubsState(null);
          setHubsError(err.message);
        }
      });
    return () => ctrl.abort();
  }, [currentKey, selection.domain, selection.purpose, selection.q]);

  const matchedHubs = selectMatchingHubs(hubsState, currentKey, search, selection.q);
  const activeTaxonomy = matchedHubs?.taxonomy ?? data.taxonomy;
  const domainGroups: DataDomainGroup[] = useMemo(() => {
    if (matchedHubs?.data_domains?.length) return matchedHubs.data_domains;
    if (activeTaxonomy.data_domains?.length) return activeTaxonomy.data_domains;
    // Preserve legacy taxonomy.domains when a unit test supplies custom domain names without data_domains.
    const hasCustomLegacy = activeTaxonomy.domains.some(
      (d) => !CANONICAL_DATA_DOMAINS.some(([slug]) => slug === d.value),
    );
    if (hasCustomLegacy && activeTaxonomy.domains.length > 0) {
      return activeTaxonomy.domains.map((d) => ({
        value: d.value,
        label: domainLabel(d.value, activeTaxonomy),
        count: d.count,
        purposes: d.purposes,
      }));
    }
    return dataDomainGroups(activeTaxonomy, data.pages);
  }, [matchedHubs, activeTaxonomy, data.pages]);

  const allMethods = data.pages.filter((p): p is PageSummary<MethodMeta> => p.meta.type === 'method' && p.meta.status !== 'archived');
  const auxiliary = allMethods.filter((p) => p.meta.method_kind !== 'analysis');
  const auxiliaryShown = auxiliary.filter((p) =>
    (kind === 'all' || p.meta.method_kind === kind)
    && (!selection.domain || domainsForMeta(p.meta).includes(selection.domain) || p.meta.tags.includes(selection.domain))
    && !selection.purpose
    && matchesMethodQuery(p.meta, search),
  );

  const fallbackAnalysisPages = useMemo(
    () => filterAnalysisMethods(data.pages, activeTaxonomy, { ...selection, q: search }),
    [data.pages, activeTaxonomy, selection, search],
  );

  const hubCards: MethodHubCard[] = useMemo(() => {
    if (kind === 'workflow' || kind === 'technical' || viewTab === 'unmapped') return [];
    if (matchedHubs) {
      return matchedHubs.methods;
    }
    return fallbackAnalysisPages.map((page) => buildFallbackMethodHub(page, data.pages, data.graph, data.flow));
  }, [kind, viewTab, matchedHubs, fallbackAnalysisPages, data.pages, data.graph, data.flow]);

  const purposeOptions = purposeOptionsFor(activeTaxonomy, selection.domain);
  const unmappedRecipes = matchedHubs?.unmapped_recipes ?? hubsState?.data.unmapped_recipes ?? [];
  const unmappedCount = matchedHubs?.unmapped_recipes_count ?? hubsState?.data.unmapped_recipes_count ?? unmappedRecipes.length;
  const totalAnalysisCount = matchedHubs?.total ?? activeTaxonomy.total;

  const title = (path: string) => byPath.get(path)?.meta.title ?? path;
  const live = (paths: string[]) => paths.filter((path) => {
    const meta = byPath.get(path)?.meta;
    return meta !== undefined && (!isItem(meta) || meta.status !== 'archived');
  });

  const href = (next: typeof selection, nextKind = kind, nextTab = '') => {
    const base = methodSelectionHref(next);
    const extra = new URLSearchParams();
    if (nextKind && nextKind !== 'all') extra.set('kind', nextKind);
    if (nextTab) extra.set('tab', nextTab);
    const suffix = extra.toString();
    return suffix ? `${base}${base.includes('?') ? '&' : '?'}${suffix}` : base;
  };
  const select = (changes: Partial<typeof selection>) =>
    href(normalizeMethodSelection({ ...selection, ...changes }, activeTaxonomy), kind === 'all' ? 'analysis' : kind);

  return (
    <section className="methods method-hub-explorer">
      <header className="gallery-top-bar">
        <div className="gallery-title-group">
          <span className="studio-eyebrow">METHOD-CENTRIC BIOINFORMATICS HUB</span>
          <h1>分析方法库</h1>
          <p className="lede">
            以科研分析方法为核心入口，聚合数据对象契约、三层配套出图模板与多重可选下游分支；方法理论就绪不等于各实现分支已独立验证。
          </p>
        </div>
        <div className="gallery-top-actions">
          <a className="button" href="#/next">多路决策沙盘</a>
          <a className="button" href="#/resources">资料与接口 ({interfaces.length})</a>
        </div>
      </header>

      {/* Top 7 Canonical Data-Type Domains Bar */}
      <nav className="domain-bar sheet" aria-label="七大数据类型域">
        <div className="domain-bar-pills">
          <a
            href={href({ domain: '', purpose: '', q: search }, 'analysis')}
            className={!selection.domain && viewTab !== 'unmapped' && kind !== 'technical' && kind !== 'workflow' ? 'domain-tab active' : 'domain-tab'}
            aria-current={!selection.domain ? 'page' : undefined}
          >
            <span>全部域</span>
            <span className="pill-count">{totalAnalysisCount}</span>
          </a>
          {domainGroups.map((domain) => (
            <a
              key={domain.value}
              href={select({ domain: domain.value })}
              className={selection.domain === domain.value && viewTab !== 'unmapped' ? 'domain-tab active' : 'domain-tab'}
              aria-current={selection.domain === domain.value ? 'page' : undefined}
            >
              <span>{domain.label || domain.value}</span>
              <span className="pill-count">{domain.count}</span>
            </a>
          ))}
        </div>

        <form
          className="method-search-inline"
          action="#/methods"
          onSubmit={(event) => {
            event.preventDefault();
            location.hash = href({ ...selection, q: search.trim() }, kind);
          }}
        >
          <input
            name="q"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="搜索方法、输出表、模板或关键词"
            aria-label="搜索方法"
          />
          <button type="submit" className="primary small">搜索</button>
          {(selection.q || selection.domain || selection.purpose) && (
            <a className="button small" href="#/methods">重置</a>
          )}
        </form>
      </nav>

      <div className="method-explorer-layout">
        {/* Left Purpose & Scope Rail */}
        <aside className="method-purpose-rail sheet" aria-label="研究目的与资料入口">
          <div className="sidebar-block">
            <span className="sidebar-label">研究目的 (Purpose)</span>
            <div className="sidebar-pills vertical">
              <a
                href={select({ purpose: '' })}
                className={!selection.purpose && viewTab !== 'unmapped' ? 'sidebar-pill active' : 'sidebar-pill'}
                aria-current={!selection.purpose ? 'page' : undefined}
              >
                <span>全部用途</span>
                <span className="pill-count">
                  {selection.domain
                    ? domainGroups.find((d) => d.value === selection.domain)?.count ?? hubCards.length
                    : totalAnalysisCount}
                </span>
              </a>
              {purposeOptions.map((purpose) => (
                <a
                  key={purpose.value}
                  href={select({ purpose: purpose.value })}
                  className={selection.purpose === purpose.value ? 'sidebar-pill active' : 'sidebar-pill'}
                  aria-current={selection.purpose === purpose.value ? 'page' : undefined}
                >
                  <span>{purpose.value}</span>
                  <span className="pill-count">{purpose.count}</span>
                </a>
              ))}
            </div>
          </div>

          <div className="sidebar-block">
            <span className="sidebar-label">附属资源与工具</span>
            <div className="sidebar-pills vertical">
              <a
                href={href({ domain: '', purpose: '', q: '' }, 'all', 'unmapped')}
                className={viewTab === 'unmapped' ? 'sidebar-pill active' : 'sidebar-pill'}
              >
                <span>未映射辅助配方</span>
                <span className="pill-count">{unmappedCount}</span>
              </a>
              <a
                href="#/resources?tab=technical"
                className={kind === 'technical' ? 'sidebar-pill active' : 'sidebar-pill'}
              >
                <span>技术与适配代码</span>
                <span className="pill-count">{allMethods.filter((m) => m.meta.method_kind === 'technical').length}</span>
              </a>
              <a
                href="#/resources?tab=workflow"
                className={kind === 'workflow' ? 'sidebar-pill active' : 'sidebar-pill'}
              >
                <span>组合流程资料</span>
                <span className="pill-count">{allMethods.filter((m) => m.meta.method_kind === 'workflow').length}</span>
              </a>
            </div>
          </div>
        </aside>

        {/* Right Method Hub Grid */}
        <div className="method-explorer-stage">
          {hubsError && (
            <p className="notice small">已使用本地目录缓存展示（实时聚合接口提示：{hubsError}）。</p>
          )}

          {viewTab === 'unmapped' ? (
            <section className="unmapped-fallback-panel">
              <div className="gallery-result-bar">
                <h2>未映射到单一方法的辅助工具配方（{unmappedCount}）</h2>
                <a className="button small" href="#/methods">返回分析方法库</a>
              </div>
              <UnmappedRecipesSection recipes={unmappedRecipes} pages={data.pages} />
            </section>
          ) : kind === 'technical' || kind === 'workflow' ? (
            <section className="method-auxiliary">
              <div className="gallery-result-bar">
                <h2>{kind === 'technical' ? '技术与适配代码' : '组合流程资料'} · {auxiliaryShown.length}</h2>
                <a className="button small" href="#/methods">返回分析方法库</a>
              </div>
              <div className="source-grid">
                {auxiliaryShown.map((page) => <MethodCodeCard key={page.path} page={page} pages={data.pages} />)}
              </div>
            </section>
          ) : (
            <>
              <div className="gallery-result-bar">
                <span className="small muted">
                  当前显示 <strong>{hubCards.length}</strong> / {totalAnalysisCount} 个核心分析方法（按方法语义去重，同一方法跨多域只计一次）
                </span>
                {unmappedCount > 0 && (
                  <a className="small" href={href({ domain: '', purpose: '', q: '' }, 'all', 'unmapped')}>
                    另有 {unmappedCount} 个未映射辅助配方 →
                  </a>
                )}
              </div>

              {hubCards.length === 0 && auxiliaryShown.length === 0 ? (
                <p className="notice">
                  没有匹配的方法。分类与搜索只缩小发现范围；可以返回全部，或在上方/左侧切换数据类型域或研究目的。
                  {' '}<a href="#/methods">查看全部</a>
                </p>
              ) : (
                <div className="method-hub-grid">
                  {hubCards.map((hub) => (
                    <HubMethodCard key={hub.id} hub={hub} taxonomy={activeTaxonomy} />
                  ))}
                </div>
              )}

              {kind === 'all' && auxiliaryShown.length > 0 && (
                <details className="method-details method-auxiliary-fold">
                  <summary>流程与技术资料（{auxiliaryShown.length} · 不计入分析方法）</summary>
                  <p className="muted small">保留资料分类与来源；同一实现的多份项目副本不重复计为分析方法。验证范围见各入口。</p>
                  <div className="source-grid">
                    {auxiliaryShown.map((page) => <MethodCodeCard key={page.path} page={page} pages={data.pages} />)}
                  </div>
                </details>
              )}
            </>
          )}

          <details className="method-details method-interfaces">
            <summary>数据接口契约（{interfaces.length} 个标准表）</summary>
            <p className="muted small">
              方法与图之间的内部执行约定。外部数据不必改名为 <code>&lt;接口&gt;.csv</code>：用 <code>render --bindings</code> 显式映射文件和列；固定文件名只保留为标准输入的兼容入口。
            </p>
            <ul className="links interface-links">
              {interfaces.map((p) => (
                <li key={p.path}>
                  <TypeMark type="interface" />
                  <a {...pageLink(p.path)}>{p.meta.title}</a>
                  <code>{p.meta.slug}.csv</code>
                  <span className="muted small"> · {live(data.flow.inputs(p.path)).map((m) => title(m)).join('、') || '暂无产出方法'}</span>
                </li>
              ))}
            </ul>
          </details>
        </div>
      </div>
    </section>
  );
}
