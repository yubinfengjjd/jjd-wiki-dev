import { useCallback, useEffect, useMemo, useState } from 'react';
import { api, GraphData, PageSummary } from './api';
import { useBackdropZone } from './backdrop/instance';
import { Flow } from './flow';
import { singlePanelKnowledge } from './figureModels';
import { RenderEnv } from './markdown';
import { useRoute } from './route';
import { Gallery } from './views/Gallery';
import { GraphView } from './views/GraphView';
import { LogView } from './views/LogView';
import { MethodsView } from './views/MethodsView';
import { PageView } from './views/PageView';
import { QueueView } from './views/QueueView';
import { pendingCount as countPending } from './workflow';

export interface AppData {
  pages: PageSummary[];
  graph: GraphData;
  flow: Flow;
  env: RenderEnv;
  reload: () => Promise<void>;
}

const NAV = [
  ['gallery', '图库'],
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
  const [error, setError] = useState('');
  const [hiddenSources, setHiddenSources] = useState<Set<string>>(new Set());

  const reload = useCallback(async () => {
    const [p, g] = await Promise.all([api.pages(), api.graph()]);
    const visible = singlePanelKnowledge(p, g);
    setPages(visible.pages);
    setGraph(visible.graph);
    setHiddenSources(visible.hiddenSources);
  }, []);

  useEffect(() => {
    reload().catch((e: Error) => setError(e.message));
  }, [reload]);

  const env = useMemo<RenderEnv>(() => ({ titles: new Map((pages ?? []).map((p) => [p.path, p.meta.title])), hiddenSources }), [pages, hiddenSources]);
  const flow = useMemo(() => new Flow(graph ?? { nodes: [], links: [] }), [graph]);

  const pendingCount = countPending(pages ?? []);

  let content;
  if (error) content = <p className="notice error">连不上本地服务（{error}）。在终端运行 wiki.py serve 后刷新页面。</p>;
  else if (!pages || !graph) content = null;
  else {
    const data: AppData = { pages, graph, flow, env, reload };
    if (route.view === 'page') content = <PageView key={route.arg} path={route.arg} data={data} />;
    else if (route.view === 'methods') content = <MethodsView data={data} />;
    else if (route.view === 'graph') content = <GraphView data={data} />;
    else if (route.view === 'queue') content = <QueueView data={data} />;
    else if (route.view === 'log') content = <LogView />;
    else content = <Gallery data={data} />;
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
