import { Component, lazy, ReactNode, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { api, effectiveStatus, GraphData, isItem, MethodTaxonomy, PageSummary } from './api';
import { useBackdropZone } from './backdrop/instance';
import { Flow } from './flow';
import { singlePanelKnowledge } from './figureModels';
import { RenderEnv } from './markdown';
import { useRoute } from './route';
import { Gallery } from './views/Gallery';
import { LogView } from './views/LogView';
import { MethodsView } from './views/MethodsView';
import { PageView } from './views/PageView';
import { QueueView } from './views/QueueView';
import { RecipesView } from './views/RecipesView';
import { ScenariosView } from './views/ScenariosView';
import { pendingCount as countPending } from './workflow';

// The force-graph engine is the heaviest module; load it only when the network is opened.
const GraphView = lazy(() => import('./views/GraphView').then((m) => ({ default: m.GraphView })));

export interface AppData {
  pages: PageSummary[];
  /** Archived whole-figure sources: hidden from browsing, listed only for traceability and deletion. */
  hiddenPages: PageSummary[];
  graph: GraphData;
  flow: Flow;
  env: RenderEnv;
  /** Derived by the backend from analysis pages; never a second frontend word list. */
  taxonomy: MethodTaxonomy;
  reload: () => Promise<void>;
}

/** One broken view must not blank the whole app; the route key resets it. */
class ViewBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    return this.state.error
      ? <p className="notice error" role="alert">这个页面显示出错（{this.state.error.message}）。返回 <a href="#/gallery">图库</a> 或刷新后重试。</p>
      : this.props.children;
  }
}

/** Graph rings and labels follow the same derived workflow as cards and the queue. */
function withEffectiveStatus(graph: GraphData, pages: PageSummary[]): GraphData {
  const byPath = new Map(pages.map((p) => [p.path, p]));
  return { ...graph, nodes: graph.nodes.map((n) => {
    const page = byPath.get(n.id);
    return page && isItem(page.meta) && page.workflow
      ? { ...n, status: effectiveStatus(page.meta, page.workflow), label: page.workflow.label } : n;
  }) };
}

const NAV = [
  ['gallery', '图库'],
  ['recipes', '配方'],
  ['scenarios', '场景'],
  ['methods', '方法库'],
  ['graph', '知识网络'],
  ['queue', '待办'],
  ['log', '日志'],
] as const;

export function App() {
  const route = useRoute();
  useBackdropZone(route.view);
  const [pages, setPages] = useState<PageSummary[] | null>(null);
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [taxonomy, setTaxonomy] = useState<MethodTaxonomy | null>(null);
  const [error, setError] = useState('');
  const [hiddenSources, setHiddenSources] = useState<Set<string>>(new Set());
  const [hiddenPages, setHiddenPages] = useState<PageSummary[]>([]);

  const reload = useCallback(async () => {
    const [p, g, t] = await Promise.all([api.pages(), api.graph(), api.methodTaxonomy()]);
    const visible = singlePanelKnowledge(p, g);
    setPages(visible.pages);
    setGraph(withEffectiveStatus(visible.graph, visible.pages));
    setTaxonomy(t);
    setHiddenSources(visible.hiddenSources);
    setHiddenPages(p.filter((page) => visible.hiddenSources.has(page.path)));
  }, []);

  useEffect(() => {
    reload().catch((e: Error) => setError(e.message));
  }, [reload]);

  const env = useMemo<RenderEnv>(() => ({ titles: new Map((pages ?? []).map((p) => [p.path, p.meta.title])), hiddenSources }), [pages, hiddenSources]);
  const flow = useMemo(() => new Flow(graph ?? { nodes: [], links: [] }), [graph]);

  const pendingCount = countPending(pages ?? []);

  let content;
  if (error) content = <p className="notice error">连不上本地服务（{error}）。在终端运行 wiki.py serve 后刷新页面。</p>;
  else if (!pages || !graph || !taxonomy) content = null;
  else {
    const data: AppData = { pages, hiddenPages, graph, flow, env, taxonomy, reload };
    if (route.view === 'page') content = <PageView key={route.arg} path={route.arg} data={data} />;
    else if (route.view === 'methods') content = <MethodsView data={data} query={route.query} />;
    else if (route.view === 'recipes') content = <RecipesView data={data} />;
    else if (route.view === 'scenarios') content = <ScenariosView data={data} />;
    else if (route.view === 'graph') content = <Suspense fallback={null}><GraphView data={data} /></Suspense>;
    else if (route.view === 'queue') content = <QueueView data={data} />;
    else if (route.view === 'log') content = <LogView />;
    else content = <Gallery data={data} />;
    content = <ViewBoundary key={`${route.view}/${route.arg}`}>{content}</ViewBoundary>;
  }

  return (
    <div className="shell">
      <header className="masthead">
        <a className="brand" href="#/gallery">
          <svg className="brand-mark" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="9" />
            <ellipse cx="12" cy="12" rx="9" ry="3.4" />
            <ellipse cx="12" cy="12" rx="3.4" ry="9" />
            <circle className="hub" cx="17.4" cy="7.6" r="2.2" />
          </svg>
          科研知识库
        </a>
        <nav aria-label="主导航">
          {NAV.map(([view, label]) => (
            <a key={view} href={`#/${view}`} className={route.view === view ? 'active' : ''}>
              {label}
              {view === 'queue' && pendingCount > 0 && <span className="count">{pendingCount}</span>}
            </a>
          ))}
        </nav>
      </header>
      <main className={route.view === 'graph' ? 'main full' : 'main'}>{content}</main>
    </div>
  );
}
