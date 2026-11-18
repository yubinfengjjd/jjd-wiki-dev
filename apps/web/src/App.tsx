import { Component, ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { effectiveStatus, GraphData, isItem, loadLibrary, MethodTaxonomy, PageSummary } from './api';
import { Flow } from './flow';
import { singlePanelKnowledge } from './figureModels';
import { RenderEnv } from './markdown';
import { useRoute } from './route';
import { FigureYaReview } from './views/FigureYaReview';
import { Gallery } from './views/Gallery';
import { LogView } from './views/LogView';
import { MethodsView } from './views/MethodsView';
import { PageView } from './views/PageView';
import { PlaybooksView } from './views/PlaybooksView';
import { ProjectsView } from './views/ProjectsView';
import { RecipesView } from './views/RecipesView';
import { ResourcesView } from './views/ResourcesView';
import { ScenariosView } from './views/ScenariosView';
import { SearchView } from './views/SearchView';
import { SourcesView } from './views/SourcesView';
import { StudioView } from './views/StudioView';

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
      ? <p className="notice error" role="alert">这个页面显示出错（{this.state.error.message}）。返回 <a href="#/methods">分析方法库</a> 或刷新后重试。</p>
      : this.props.children;
  }
}

/** Graph rings and labels follow the same derived workflow as cards. */
function withEffectiveStatus(graph: GraphData, pages: PageSummary[]): GraphData {
  const byPath = new Map(pages.map((p) => [p.path, p]));
  return {
    ...graph,
    nodes: graph.nodes.map((n) => {
      const page = byPath.get(n.id);
      return page && isItem(page.meta) && page.workflow
        ? { ...n, status: effectiveStatus(page.meta, page.workflow), label: page.workflow.label }
        : n;
    }),
  };
}

const NAV = [
  ['methods', '分析方法库'],
  ['recipes', 'FigureYa 配方库'],
  ['next', '多路决策沙盘'],
  ['projects', '课题记录'],
  ['resources', '资料与检索'],
] as const;

function isNavActive(navView: (typeof NAV)[number][0], currentView: string): boolean {
  if (navView === 'methods') return currentView === 'methods';
  if (navView === 'recipes') return currentView === 'recipes' || currentView === 'figureya';
  if (navView === 'next') return currentView === 'next' || currentView === 'playbooks';
  if (navView === 'projects') return currentView === 'projects';
  if (navView === 'resources') {
    return ['resources', 'search', 'gallery', 'sources', 'scenarios', 'log'].includes(currentView);
  }
  return false;
}

export function App() {
  const route = useRoute();
  const [pages, setPages] = useState<PageSummary[] | null>(null);
  const [graph, setGraph] = useState<GraphData>({ nodes: [], links: [] });
  const [taxonomy, setTaxonomy] = useState<MethodTaxonomy>({ total: 0, domains: [], purposes: [], unclassified: [] });
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(true);
  const [backgroundErrors, setBackgroundErrors] = useState<string[]>([]);
  const generation = useRef(0);
  // Search and detail fetch their own current evidence; neither needs a full
  // background graph and every other page's verification before it can be read.
  const hydrateLibrary = route.view !== 'search' && route.view !== 'page';

  const reload = useCallback(async () => {
    const own = ++generation.current;
    const current = () => generation.current === own;
    setChecking(true);
    setError('');
    setBackgroundErrors([]);
    try {
      await loadLibrary({
        pages: setPages,
        graph: setGraph,
        taxonomy: setTaxonomy,
        error: (message) => setBackgroundErrors((previous) => [...previous, message]),
      }, current, hydrateLibrary);
    } catch (failure) {
      if (current()) setError((failure as Error).message);
    } finally {
      if (current()) setChecking(false);
    }
  }, [hydrateLibrary]);

  useEffect(() => {
    void reload();
    return () => { generation.current++; };
  }, [reload]);

  const visible = useMemo(() => singlePanelKnowledge(pages ?? [], graph), [pages, graph]);
  const displayedGraph = useMemo(() => withEffectiveStatus(visible.graph, visible.pages), [visible]);
  const env = useMemo<RenderEnv>(() => ({
    titles: new Map(visible.pages.map((p) => [p.path, p.meta.title])),
    hiddenSources: visible.hiddenSources,
  }), [visible]);
  const flow = useMemo(() => new Flow(displayedGraph), [displayedGraph]);

  let content;
  if (error) content = <p className="notice error">连不上本地服务（{error}）。在终端运行 wiki.py serve 后刷新页面。</p>;
  else if (!pages) content = <p className="notice" role="status">正在读取目录…</p>;
  else {
    const data: AppData = {
      pages: visible.pages,
      hiddenPages: pages.filter((page) => visible.hiddenSources.has(page.path)),
      graph: displayedGraph,
      flow,
      env,
      taxonomy,
      reload,
    };
    if (route.view === 'page') content = <PageView key={route.arg} path={route.arg} query={route.query} data={data} />;
    else if (route.view === 'studio') content = <StudioView data={data} query={route.query} />;
    else if (route.view === 'projects') content = <ProjectsView data={data} />;
    else if (route.view === 'search') content = <SearchView query={route.query} />;
    else if (route.view === 'next' || route.view === 'playbooks') content = <PlaybooksView data={data} query={route.query} />;
    else if (route.view === 'resources') content = <ResourcesView data={data} query={route.query} />;
    else if (route.view === 'recipes') content = <RecipesView data={data} query={route.query} />;
    else if (route.view === 'sources') content = <SourcesView data={data} query={route.query} />;
    else if (route.view === 'figureya') content = <FigureYaReview data={data} />;
    else if (route.view === 'scenarios') content = <ScenariosView data={data} />;
    else if (route.view === 'gallery') content = <Gallery data={data} />;
    else if (route.view === 'log') content = <LogView />;
    else content = <MethodsView data={data} query={route.query} />;
    content = <ViewBoundary key={`${route.view}/${route.arg}`}>{content}</ViewBoundary>;
  }

  return (
    <div className="shell">
      <header className="masthead">
        <a className="brand" href="#/methods">
          <svg className="brand-mark" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="9" />
            <ellipse cx="12" cy="12" rx="9" ry="3.4" />
            <ellipse cx="12" cy="12" rx="3.4" ry="9" />
            <circle className="hub" cx="17.4" cy="7.6" r="2.2" />
          </svg>
          <span>Bio-Template Studio</span>
        </a>
        <nav aria-label="主导航">
          {NAV.map(([view, label]) => (
            <a key={view} href={`#/${view}`} className={isNavActive(view, route.view) ? 'active' : ''}>
              {label}
            </a>
          ))}
        </nav>
        <button type="button" className="library-refresh" disabled={checking} onClick={() => void reload()}>
          {checking ? '正在同步…' : '同步知识库'}
        </button>
      </header>
      <main className={route.view === 'studio' ? 'main full studio-main' : 'main'}>
        {pages && checking && <p className="notice small" role="status">目录已加载，正在核对运行证据与关联。</p>}
        {backgroundErrors.length > 0 && (
          <p className="notice error" role="alert">
            部分证据或关联未加载完成：{backgroundErrors.join('；')} <button onClick={() => void reload()}>重试</button>
          </p>
        )}
        {content}
      </main>
    </div>
  );
}
