import { useState } from 'react';
import { PageSummary, RecipeMeta, stageStatus } from '../api';
import type { AppData } from '../App';
import { RecipeCard } from '../components';
import { RECIPE_STAGES, recipeOrigin, recipeStage } from '../recipes';

interface Filters {
  q: string;
  stage: string;
  chart: string;
  favorite: boolean;
}

const EMPTY: Filters = { q: '', stage: '', chart: '', favorite: false };

function matches(meta: RecipeMeta, origin: string, f: Filters): boolean {
  if (f.stage && recipeStage(meta) !== f.stage) return false;
  if (f.chart && !(meta.chart_types ?? []).includes(f.chart)) return false;
  if (f.favorite && !meta.favorite) return false;
  const words = f.q.toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return true;
  const haystack = [meta.id, meta.title, meta.summary ?? '', origin, ...(meta.tags ?? []), ...(meta.keywords ?? []), ...(meta.chart_types ?? [])]
    .join(' ')
    .toLowerCase();
  return words.every((word) => haystack.includes(word));
}

/** L1 recipes: whole upstream modules run as-is; archived ones are listed in the queue. */
export function RecipesView({ data }: { data: AppData }) {
  const [f, setF] = useState<Filters>(EMPTY);
  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => setF({ ...f, [key]: value });
  const recipes = data.pages
    .filter((p): p is PageSummary<RecipeMeta> => p.meta.type === 'recipe' && p.meta.status !== 'archived')
    .map((p) => ({ ...p, origin: recipeOrigin(p.meta, data.env.titles) }));
  const shown = recipes.filter((p) => matches(p.meta, p.origin, f));
  const charts = [...new Set(recipes.flatMap((p) => p.meta.chart_types ?? []))].sort();

  return (
    <section className="recipes">
      <header className="hero slim">
        <div className="hero-text">
          <h1>配方</h1>
          <p className="lede">
            整个上游模块原字节入库，在 Wiki 专用环境原样运行并留收据。卡片上的图是最近一次通过的原样运行图；运行通过只说明在记录的环境里跑通，不等于科学有效。使用前核对许可与应引用的文献。
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

      <div className="filters" role="search">
        <input type="search" placeholder="搜索标题、来源条目、标签、关键词" aria-label="搜索配方" value={f.q} onChange={(e) => set('q', e.target.value)} />
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
      </div>

      {shown.length === 0 ? (
        <p className="notice">
          {recipes.length > 0
            ? '没有符合筛选条件的配方，换个关键词或清空筛选再试。'
            : '还没有配方。在 agent 里把来源库条目升级为配方（wiki.py promote）后会出现在这里。'}
        </p>
      ) : (
        <div className="grid">
          {shown.map((p, i) => (
            <RecipeCard key={p.path} path={p.path} meta={p.meta} number={i + 1} origin={p.origin} />
          ))}
        </div>
      )}
    </section>
  );
}
