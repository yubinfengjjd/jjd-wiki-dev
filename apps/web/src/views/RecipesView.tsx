import { useEffect, useMemo, useState } from 'react';
import {
  api,
  MethodHubCard,
  MethodHubsResponse,
  PageSummary,
  RecipeMeta,
  stageStatus,
} from '../api';
import type { AppData } from '../App';
import { RecipeCard } from '../components';
import { CANONICAL_DATA_DOMAINS, DATA_DOMAIN_LABEL } from '../methods';
import { pageLink } from '../nav';
import { RECIPE_STAGES, recipeOrigin, recipeStage, matchesRecipeQuery } from '../recipes';

interface Filters {
  q: string;
  stage: string;
  chart: string;
  favorite: boolean;
  domain: string;
  method: string;
  groupByMethod: boolean;
}

function parseRecipeFilterQuery(query = ''): Pick<Filters, 'domain' | 'method' | 'q'> {
  const params = new URLSearchParams(query.replace(/^\?/, ''));
  return {
    domain: params.get('domain') ?? '',
    method: params.get('method') ?? '',
    q: params.get('q') ?? '',
  };
}

function recipeRouteHref(domain: string, method: string): string {
  const params = new URLSearchParams();
  if (domain) params.set('domain', domain);
  if (method) params.set('method', method);
  const qs = params.toString();
  return qs ? `#/recipes?${qs}` : '#/recipes';
}

function matches(meta: RecipeMeta, origin: string, f: Filters): boolean {
  if (f.stage && recipeStage(meta) !== f.stage) return false;
  if (f.chart && !(meta.chart_types ?? []).includes(f.chart)) return false;
  if (f.favorite && !meta.favorite) return false;
  return matchesRecipeQuery(meta, origin, f.q);
}

export interface RecipeMethodIndex {
  methodsById: Map<string, MethodHubCard>;
  methodsForRecipe: Map<string, MethodHubCard[]>;
  unmappedIds: Set<string>;
}

export function buildRecipeMethodIndex(hubs: MethodHubsResponse | null): RecipeMethodIndex {
  const methodsById = new Map<string, MethodHubCard>();
  const methodsForRecipe = new Map<string, MethodHubCard[]>();
  const unmappedIds = new Set<string>();
  if (!hubs) return { methodsById, methodsForRecipe, unmappedIds };

  for (const hub of hubs.methods) {
    methodsById.set(hub.id, hub);
    for (const rec of hub.reference_recipes) {
      const list = methodsForRecipe.get(rec.id) ?? [];
      if (!list.some((existing) => existing.id === hub.id)) {
        list.push(hub);
        methodsForRecipe.set(rec.id, list);
      }
    }
  }
  for (const rec of hubs.unmapped_recipes) {
    unmappedIds.add(rec.id);
  }
  return { methodsById, methodsForRecipe, unmappedIds };
}

/** Legacy read-only recipe archive: whole upstream modules organized by 7 canonical data domains and analysis methods. */
export function RecipesView({ data, query = '' }: { data: AppData; query?: string }) {
  const initialQuery = parseRecipeFilterQuery(query);
  const [f, setF] = useState<Filters>({
    q: initialQuery.q,
    stage: '',
    chart: '',
    favorite: false,
    domain: initialQuery.domain,
    method: initialQuery.method,
    groupByMethod: true,
  });
  const [hubs, setHubs] = useState<MethodHubsResponse | null>(null);

  useEffect(() => {
    const parsed = parseRecipeFilterQuery(query);
    setF((prev) => ({
      ...prev,
      domain: parsed.domain,
      method: parsed.method,
      q: parsed.q || prev.q,
    }));
  }, [query]);

  useEffect(() => {
    const ctrl = new AbortController();
    api.methodHubs(undefined, ctrl.signal)
      .then((res) => setHubs(res))
      .catch(() => {
        /* fallback gracefully to flat recipe view if offline/SSR */
      });
    return () => ctrl.abort();
  }, [data.mutationRevision]);

  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => setF((prev) => ({ ...prev, [key]: value }));

  const syncHash = (nextDomain: string, nextMethod: string) => {
    setF((prev) => ({ ...prev, domain: nextDomain, method: nextMethod }));
    if (typeof location !== 'undefined') {
      location.hash = recipeRouteHref(nextDomain, nextMethod);
    }
  };

  const recipes = useMemo(
    () =>
      data.pages
        .filter((p): p is PageSummary<RecipeMeta> => p.meta.type === 'recipe' && p.meta.status !== 'archived')
        .map((p) => ({ ...p, origin: recipeOrigin(p.meta, data.env.titles) })),
    [data.pages, data.env.titles],
  );

  const methodIndex = useMemo(() => buildRecipeMethodIndex(hubs), [hubs]);

  const domainRecipeCounts = useMemo(() => {
    const counts = new Map<string, number>();
    if (!hubs) return counts;
    for (const [slug] of CANONICAL_DATA_DOMAINS) {
      const seen = new Set<string>();
      for (const hub of hubs.methods) {
        if (!hub.data_domains.includes(slug)) continue;
        for (const rec of hub.reference_recipes) seen.add(rec.id);
      }
      counts.set(slug, seen.size);
    }
    return counts;
  }, [hubs]);

  const methodsInSelectedDomain = useMemo(() => {
    if (!hubs) return [] as MethodHubCard[];
    return hubs.methods
      .filter((hub) => hub.reference_recipes.length > 0 && (!f.domain || hub.data_domains.includes(f.domain)))
      .sort((a, b) => b.reference_recipes.length - a.reference_recipes.length || a.title.localeCompare(b.title));
  }, [hubs, f.domain]);

  const shown = useMemo(() => {
    return recipes.filter((p) => {
      if (!matches(p.meta, p.origin, f)) return false;
      if (!hubs) return true;
      const mappedMethods = methodIndex.methodsForRecipe.get(p.meta.id) ?? [];
      if (f.domain === 'unmapped') {
        return mappedMethods.length === 0;
      }
      if (f.domain && !mappedMethods.some((m) => m.data_domains.includes(f.domain))) {
        return false;
      }
      if (f.method && !mappedMethods.some((m) => m.id === f.method)) {
        return false;
      }
      return true;
    });
  }, [recipes, f, hubs, methodIndex]);

  const groupedByMethod = useMemo(() => {
    if (!hubs || !f.groupByMethod) return null;
    const groups = new Map<string, { hub: MethodHubCard | null; items: typeof shown }>();
    for (const item of shown) {
      const candidates = methodIndex.methodsForRecipe.get(item.meta.id) ?? [];
      let chosen: MethodHubCard | null = null;
      if (f.method) {
        chosen = candidates.find((m) => m.id === f.method) ?? null;
      } else if (f.domain && f.domain !== 'unmapped') {
        chosen = candidates.find((m) => m.data_domains.includes(f.domain)) ?? candidates[0] ?? null;
      } else {
        chosen = candidates[0] ?? null;
      }
      const groupKey = chosen ? chosen.id : '__unmapped__';
      const entry = groups.get(groupKey) ?? { hub: chosen, items: [] };
      entry.items.push(item);
      groups.set(groupKey, entry);
    }
    const order = CANONICAL_DATA_DOMAINS.map(([d]) => d);
    return [...groups.values()].sort((a, b) => {
      if (!a.hub) return 1;
      if (!b.hub) return -1;
      const da = order.indexOf(a.hub.data_domains[0] ?? '');
      const db = order.indexOf(b.hub.data_domains[0] ?? '');
      if (da !== db) return (da === -1 ? 99 : da) - (db === -1 ? 99 : db);
      return b.items.length - a.items.length || a.hub.title.localeCompare(b.hub.title);
    });
  }, [hubs, f.groupByMethod, f.domain, f.method, shown, methodIndex]);

  const charts = [...new Set(recipes.flatMap((p) => p.meta.chart_types ?? []))].sort();

  const renderRecipeEntry = (p: (typeof shown)[number], index: number) => {
    const mappedMethods = methodIndex.methodsForRecipe.get(p.meta.id) ?? [];
    return (
      <div key={p.path} className="recipe-hub-item">
        <RecipeCard path={p.path} meta={p.meta} number={index + 1} origin={p.origin} />
        {hubs && (
          <div className="recipe-method-chips">
            {mappedMethods.length > 0 ? (
              mappedMethods.map((m) => (
                <a
                  key={m.id}
                  className="recipe-method-chip"
                  {...pageLink(m.path)}
                  title={`${m.data_domain_labels.join(' / ')} · 点击进入该方法工作台`}
                >
                  <span className="recipe-chip-domain">{m.data_domain_labels[0] || DATA_DOMAIN_LABEL[m.data_domains[0]] || '方法'}</span>
                  <span>{m.title}</span>
                </a>
              ))
            ) : (
              <span className="recipe-method-chip muted">通用辅助工具（未绑定分析方法）</span>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <section className="recipes">
      <header className="hero slim">
        <div className="hero-text">
          <h1>历史归档模板（按方法域与分析方法组织）</h1>
          <p className="lede">
            历史归档的上游 FigureYa 整模块源码，已按 7 大数据类型域与细分分析方法建立映射（只读历史参考，新增绘图模板统一建入绘图模板库）；卡片上的图是最近一次通过的参考运行图，不代表独立科学有效验证，使用前请核对非商业许可与引用文献。
          </p>
          <dl className="census">
            {RECIPE_STAGES.map(([stage, label]) => (
              <div key={stage}>
                <dt>
                  <span className={`dot status-${stageStatus(stage) ?? stage}`} aria-hidden="true" />
                  {label}
                </dt>
                <dd>{recipes.filter((p) => recipeStage(p.meta) === stage).length}</dd>
              </div>
            ))}
          </dl>
        </div>
      </header>

      {hubs && (
        <nav className="recipes-domain-tabs" aria-label="按方法数据类型域筛选历史归档模板">
          <button
            type="button"
            className={!f.domain ? 'domain-tab active' : 'domain-tab'}
            onClick={() => syncHash('', '')}
          >
            <span>全部方法域</span>
            <span className="domain-tab-count">{recipes.length}</span>
          </button>
          {CANONICAL_DATA_DOMAINS.map(([slug, label]) => (
            <button
              key={slug}
              type="button"
              className={f.domain === slug ? 'domain-tab active' : 'domain-tab'}
              onClick={() => syncHash(slug, '')}
            >
              <span>{label}</span>
              <span className="domain-tab-count">{domainRecipeCounts.get(slug) ?? 0}</span>
            </button>
          ))}
          {hubs.unmapped_recipes_count > 0 && (
            <button
              type="button"
              className={f.domain === 'unmapped' ? 'domain-tab active' : 'domain-tab'}
              onClick={() => syncHash('unmapped', '')}
            >
              <span>通用辅助工具</span>
              <span className="domain-tab-count">{hubs.unmapped_recipes_count}</span>
            </button>
          )}
        </nav>
      )}

      <div className="filters" role="search">
        <input
          type="search"
          placeholder="搜索标题、来源条目、标签、关键词"
          aria-label="搜索历史归档模板"
          value={f.q}
          onChange={(e) => set('q', e.target.value)}
        />
        {hubs && f.domain !== 'unmapped' && (
          <select
            aria-label="所属分析方法"
            value={f.method}
            onChange={(e) => syncHash(f.domain, e.target.value)}
          >
            <option value="">全部关联分析方法</option>
            {methodsInSelectedDomain.map((m) => (
              <option key={m.id} value={m.id}>
                {m.title}（{m.reference_recipes.length}）
              </option>
            ))}
          </select>
        )}
        <select aria-label="状态" value={f.stage} onChange={(e) => set('stage', e.target.value)}>
          <option value="">全部状态</option>
          {RECIPE_STAGES.map(([stage, label]) => (
            <option key={stage} value={stage}>{label}</option>
          ))}
        </select>
        <select aria-label="图型" value={f.chart} onChange={(e) => set('chart', e.target.value)}>
          <option value="">全部图型</option>
          {charts.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <label className="check">
          <input type="checkbox" checked={f.favorite} onChange={(e) => set('favorite', e.target.checked)} />
          只看收藏
        </label>
        {hubs && (
          <label className="check">
            <input
              type="checkbox"
              checked={f.groupByMethod}
              onChange={(e) => set('groupByMethod', e.target.checked)}
            />
            按方法分组
          </label>
        )}
      </div>

      {shown.length === 0 ? (
        <p className="notice">
          {recipes.length > 0
            ? '没有符合筛选条件的历史归档模板，换个方法域、关键词或清空筛选再试。'
            : '还没有历史归档模板。新增绘图模板统一建入绘图模板库。'}
        </p>
      ) : groupedByMethod ? (
        <div className="recipe-method-groups">
          {groupedByMethod.map((group) => (
            <section
              key={group.hub ? group.hub.id : 'unmapped'}
              className="recipe-method-group"
              aria-label={group.hub ? group.hub.title : '通用辅助工具'}
            >
              <header className="recipe-method-group-head">
                <div className="recipe-method-group-title">
                  {group.hub ? (
                    <>
                      <div className="recipe-group-domains">
                        {group.hub.data_domain_labels.map((label) => (
                          <span key={label} className="domain-pill">{label}</span>
                        ))}
                      </div>
                      <h2>
                        <a {...pageLink(group.hub.path)}>{group.hub.title}</a>
                        <span className="recipe-group-count">（{group.items.length}）</span>
                      </h2>
                    </>
                  ) : (
                    <h2>
                      <span>通用辅助工具（未绑定分析方法）</span>
                      <span className="recipe-group-count">（{group.items.length}）</span>
                    </h2>
                  )}
                </div>
                {group.hub && (
                  <a className="button small" {...pageLink(group.hub.path)}>
                    进入方法工作台 →
                  </a>
                )}
              </header>
              <div className="grid">
                {group.items.map((p, i) => renderRecipeEntry(p, i))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <div className="grid">
          {shown.map((p, i) => renderRecipeEntry(p, i))}
        </div>
      )}
    </section>
  );
}
