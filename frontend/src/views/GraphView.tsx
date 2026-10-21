import { useEffect, useMemo, useRef, useState } from 'react';
import { GraphNode, imageOf, PageType, STATUS_LABEL, Status, TYPE_LABEL } from '../api';
import type { AppData } from '../App';
import { StatusBadge, TypeMark } from '../components';
import { ForceGraph } from '../graph/ForceGraph';
import { openPage } from '../nav';
import { HAS_STATUS } from '../palette';

const TYPES: PageType[] = ['chart-type', 'layout', 'template', 'method', 'interface', 'project'];
const STATUSES: [Status, string][] = [
  ['pending_signoff', '待你签核 / 确认'],
  ['pending_template', '等 agent 处理'],
  ['ready', '可用'],
];

interface Hover {
  id: string;
  x: number;
  y: number;
}

export function GraphView({ data }: { data: AppData }) {
  const host = useRef<HTMLDivElement>(null);
  const engine = useRef<ForceGraph | null>(null);
  const [hover, setHover] = useState<Hover | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [hidden, setHidden] = useState<Set<PageType>>(new Set());
  const [showArchived, setShowArchived] = useState(false);
  const [dims, setDims] = useState<2 | 3>(2);
  const [query, setQuery] = useState('');

  const nodes = useMemo(() => new Map(data.graph.nodes.map((n) => [n.id, n])), [data.graph]);
  const metaOf = useMemo(() => new Map(data.pages.map((p) => [p.path, p.meta])), [data.pages]);

  useEffect(() => {
    const graph = new ForceGraph(host.current!, data.graph);
    engine.current = graph;
    graph.on('hover', (id, x, y) => setHover(id ? { id, x, y } : null));
    graph.on('select', setSelected);
    graph.on('open', (id) => openPage(id));
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && graph.select(null);
    addEventListener('keydown', onKey);
    return () => {
      removeEventListener('keydown', onKey);
      graph.dispose();
      engine.current = null;
    };
    // Created once; later data arrives through setData so the layout is kept.
  }, []);

  useEffect(() => engine.current?.setData(data.graph), [data.graph]);
  useEffect(() => engine.current?.setFilter(hidden, showArchived), [hidden, showArchived]);

  const toggleType = (t: PageType) => {
    const next = new Set(hidden);
    if (next.has(t)) next.delete(t);
    else next.add(t);
    setHidden(next);
  };

  const toggleDims = () => {
    const next = dims === 2 ? 3 : 2;
    engine.current!.setDimensions(next);
    setDims(next);
  };

  const matches = query.trim()
    ? data.graph.nodes.filter((n) => n.title.toLowerCase().includes(query.trim().toLowerCase())).slice(0, 6)
    : [];
  const count = (pred: (n: GraphNode) => boolean) => data.graph.nodes.filter(pred).length;
  const thumbFor = (id: string) => {
    const meta = metaOf.get(id);
    return meta ? imageOf(meta) : null;
  };

  return (
    <div className="graph-page">
      <div className="graph-stage" ref={host} aria-label="知识网络图。拖动画布平移，拖动节点调整位置，滚轮缩放，单击节点查看，双击打开。" />

      <aside className="legend sheet">
        <h2>知识网络</h2>
        <p className="muted small">
          {count(() => true)} 页，{data.graph.links.length} 条链接。拖节点会带动相连的节点，单击查看，双击打开。带箭头的紫线是“分析 → 数据接口 → 出图”。
        </p>
        <div className="finder">
          <input type="search" placeholder="查找页面" aria-label="按标题查找" value={query} onChange={(e) => setQuery(e.target.value)} />
          {matches.length > 0 && (
            <ul>
              {matches.map((n) => (
                <li key={n.id}>
                  <button
                    className="link-button"
                    onClick={() => {
                      engine.current!.select(n.id);
                      setQuery('');
                    }}
                  >
                    <span className={`dot ${dotClass(n)}`} aria-hidden="true" />
                    {n.title}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <h3>页面类型</h3>
        <ul className="legend-list">
          {TYPES.map((t) => (
            <li key={t}>
              <label className="check">
                <input type="checkbox" checked={!hidden.has(t)} onChange={() => toggleType(t)} />
                <TypeMark type={t} />
                {TYPE_LABEL[t]}
                <span className="muted">{count((n) => n.type === t)}</span>
              </label>
            </li>
          ))}
        </ul>

        <h3>外圈颜色（图、模板、方法）</h3>
        <ul className="legend-list">
          {STATUSES.map(([s, label]) => (
            <li key={s}>
              <span className={`ring status-${s}`} aria-hidden="true" />
              {label}
            </li>
          ))}
          <li>
            <label className="check">
              <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} />
              显示已归档
            </label>
          </li>
        </ul>
      </aside>

      <div className="graph-tools">
        <button onClick={toggleDims} aria-pressed={dims === 3}>{dims === 2 ? '立体视图' : '平面视图'}</button>
        <button onClick={() => engine.current!.fit()}>全部显示</button>
      </div>

      {hover && hover.id !== selected && <HoverCard node={nodes.get(hover.id)!} x={hover.x} y={hover.y} thumb={thumbFor(hover.id)} />}

      <NodePanel
        node={selected ? nodes.get(selected) ?? null : null}
        thumb={selected ? thumbFor(selected) : null}
        neighbours={selected ? neighboursOf(selected, data, nodes) : []}
        onPick={(id) => engine.current!.select(id)}
        onClose={() => engine.current!.select(null)}
      />
    </div>
  );
}

const dotClass = (n: GraphNode) => (HAS_STATUS(n.type) ? `status-${n.status}` : `type-${n.type}`);

function neighboursOf(id: string, data: AppData, nodes: Map<string, GraphNode>) {
  const ids = new Set<string>();
  for (const l of data.graph.links) {
    if (l.source === id) ids.add(l.target);
    if (l.target === id) ids.add(l.source);
  }
  return [...ids].flatMap((n) => nodes.get(n) ?? []).sort((a, b) => TYPES.indexOf(a.type) - TYPES.indexOf(b.type));
}

function HoverCard({ node, x, y, thumb }: { node: GraphNode; x: number; y: number; thumb: string | null }) {
  const flip = x > innerWidth - 300;
  return (
    <div className="hover-card sheet" style={{ left: flip ? x - 276 : x + 18, top: Math.min(y + 18, innerHeight - 230) }} role="tooltip">
      {thumb && (
        <div className="plate">
          <img src={thumb} alt="" />
        </div>
      )}
      <strong>{node.title}</strong>
      <span className="muted small">{TYPE_LABEL[node.type]}{HAS_STATUS(node.type) && node.status ? `，${STATUS_LABEL[node.status]}` : ''}</span>
    </div>
  );
}

interface PanelProps {
  node: GraphNode | null;
  thumb: string | null;
  neighbours: GraphNode[];
  onPick: (id: string) => void;
  onClose: () => void;
}

function NodePanel({ node, thumb, neighbours, onPick, onClose }: PanelProps) {
  return (
    <aside className={node ? 'node-panel sheet open' : 'node-panel sheet'} aria-hidden={!node} aria-label="所选页面">
      {node && (
        <>
          <div className="panel-row">
            <span className="muted small">{TYPE_LABEL[node.type]}</span>
            <button className="ghost small" onClick={onClose}>关闭</button>
          </div>
          <h2>{node.title}</h2>
          {HAS_STATUS(node.type) && node.status && <StatusBadge status={node.status} />}
          {thumb && (
            <div className="plate">
              <img src={thumb} alt={node.title} />
            </div>
          )}
          <button className="primary" onClick={() => openPage(node.id)}>打开页面</button>
          <h3>相连的页面 {neighbours.length}</h3>
          <ul className="links">
            {neighbours.map((n) => (
              <li key={n.id}>
                <button className="link-button" onClick={() => onPick(n.id)}>
                  <span className={`dot ${dotClass(n)}`} aria-hidden="true" />
                  {n.title}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </aside>
  );
}
