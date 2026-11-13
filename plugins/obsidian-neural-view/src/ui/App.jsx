import React, {useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState} from 'react';
import {MODULES, KINDS} from '../graph.mjs';
import {layoutGraph} from '../adapter.mjs';
import {Scene, targets, sp} from '../vendor/Scene.jsx';
import {NetworkCanvas} from '../vendor/NetworkCanvas.jsx';
import {Icon} from '../vendor/icons.jsx';

const PAGE_SIZE = 11;
function Detail({node, graph, onGo, onOpen, onClose}) {
  const category = KINDS[node.kind];
  const incoming = graph.nodes.filter(n => n.id !== node.id && n.references.some(r => r.path === node.path));
  const raw = node.rawStatus === undefined ? null : typeof node.rawStatus === 'string' ? node.rawStatus : JSON.stringify(node.rawStatus);
  return <aside className="analysis-wrap" aria-label="笔记详情">
    <div className="analysis glass"><div className="an-scroll">
      <header className="an-head"><span className="an-cat" style={{color: category.color}}>{category.label} <em>{category.en}</em></span><button className="icon-btn" aria-label="关闭详情" onClick={onClose}><Icon name="close" size={14}/></button></header>
      <div className="an-title-row"><h2>{node.title}</h2>{node.thumbnail && <img className="an-cover" src={node.thumbnail} alt="笔记原有缩略图"/>}</div>
      <p className="an-full">{node.path}</p>
      {raw !== null && <div className="an-status"><p>原始字段 <em>Raw frontmatter</em></p><code>status: {raw}</code></div>}
      <div className="an-actions"><button className="pill primary" onClick={() => onOpen(node.path, node.path)}>打开原生笔记 <em>Open note</em></button></div>
      <section className="neural-reference-list"><h3>已有页面引用 <em>Explicit wikilinks</em></h3>
        {node.references.length ? node.references.map((reference, i) => <div key={i}>
          {reference.resolved ? <button className="neural-reference" onClick={() => onGo(reference.path)}>{reference.label}<small>{reference.path}</small></button> : <span className="neural-unresolved">{reference.label}<small>{reference.excluded ? '不在五类正式条目范围 / Outside graph scope' : '未解析 / Unresolved'}</small></span>}
        </div>) : <p className="quiet">暂无页面引用 <em>No wikilinks</em></p>}
      </section>
      <section className="neural-reference-list"><h3>引用此页 <em>Backlinks</em></h3>{incoming.length ? incoming.map(n => <button key={n.id} className="neural-reference" onClick={() => onGo(n.id)}>{n.title}<small>{n.path}</small></button>) : <p className="quiet">暂无入链 <em>No backlinks</em></p>}</section>
      <p className="neural-boundary">连线仅表示页面引用。兼容性、签核及业务操作请在原有网页或 CLI 中查看和处理。</p>
    </div></div>
  </aside>;
}
export function NeuralApp({graph, media: resourcePaths, onOpen, onRefresh, hidden = false, error}) {
  const stageRef = useRef(null);
  const [size, setSize] = useState({w: 1280, h: 760});
  const [focus, setFocus] = useState({mod: null, sel: null});
  const [paused, setPaused] = useState(false);
  const [page, setPage] = useState(0);
  const [query, setQuery] = useState('');
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const {mod, sel} = focus;
  const node = graph.index.get(sel);
  const stage = node ? 'note' : mod ? 'module' : 'hub';
  const allItems = useMemo(() => graph.nodes.filter(n => n.kind === mod && (!query || `${n.title}\n${n.path}`.toLocaleLowerCase().includes(query.toLocaleLowerCase()))), [graph, mod, query]);
  const pages = Math.max(1, Math.ceil(allItems.length / PAGE_SIZE));
  const safePage = Math.min(page, pages - 1);
  const items = useMemo(() => allItems.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE), [allItems, safePage]);
  const layout = useMemo(() => layoutGraph(graph), [graph]);
  const media = useMemo(() => ({orb: resourcePaths['orb.mp4'], orbPoster: resourcePaths['orb.jpg'], jelly: resourcePaths['jellyfish.mp4'], jellyPoster: resourcePaths['jellyfish.jpg']}), [resourcePaths]);
  const live = useRef(null);
  if (!live.current) {
    const now = performance.now();
    live.current = {t0: now, time: 0, stage, mod, items, size, reduced, paused, hidden, hover: null, itemState: [], fanStart: now, orb: {x: 640, y: 380, s: 400},
      springs: {dust: sp(.3), orb: {x: sp(640), y: sp(380), s: sp(120), o: sp(0)}, jelly: Object.fromEntries(MODULES.map(m => [m.id, {x: sp(640), y: sp(380), s: sp(20), o: sp(0), lo: sp(0)}]))}};
    if (reduced) live.current.t0 = now - 6000;
  }
  Object.assign(live.current, {stage, mod, items, size, reduced, paused, hidden});
  useLayoutEffect(() => {
    const element = stageRef.current;
    const measure = () => {
      const w = element.clientWidth, h = element.clientHeight, L = live.current;
      if (!w || !h) return;
      if (L.stage === 'hub' && performance.now() - L.t0 < 300) {
        const orb = targets({...L, size: {w, h}}, 0).orb;
        Object.assign(L.springs.orb, {x: sp(orb.x), y: sp(orb.y)});
        for (const m of MODULES) Object.assign(L.springs.jelly[m.id], {x: sp(orb.x), y: sp(orb.y)});
      }
      setSize({w, h});
    };
    measure(); const observer = new ResizeObserver(measure); observer.observe(element);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const change = () => setReduced(preference.matches);
    preference.addEventListener('change', change);
    return () => preference.removeEventListener('change', change);
  }, []);
  useEffect(() => { live.current.syncVideo?.(); }, [paused, hidden, reduced, media]);
  useEffect(() => {
    if (sel && !graph.index.has(sel)) setFocus({mod, sel: null});
  }, [graph, sel, mod]);
  const selectModule = id => { setFocus({mod: id, sel: null}); setPage(0); setQuery(''); };
  const go = useCallback(id => {
    const n = graph.index.get(id);
    if (!n) return;
    setQuery('');
    setPage(Math.floor(graph.nodes.filter(x => x.kind === n.kind).findIndex(x => x.id === id) / PAGE_SIZE));
    setFocus({mod: n.kind, sel: id});
  }, [graph]);
  const replay = () => {
    const L = live.current; L.t0 = performance.now(); L.time = 0;
    Object.assign(L.springs.orb, {s: sp(120), o: sp(0)});
    for (const m of MODULES) Object.assign(L.springs.jelly[m.id], {x: sp(L.orb.x), y: sp(L.orb.y), s: sp(20), o: sp(0), lo: sp(0)});
    setFocus({mod: null, sel: null});
  };
  const category = MODULES.find(m => m.id === mod);
  return <div className="neural" data-paused={paused || hidden ? 'true' : 'false'} onKeyDown={event => {
    if (event.key === 'Escape' && !event.isComposing) { event.stopPropagation(); setFocus(sel ? {mod, sel: null} : {mod: null, sel: null}); }
  }}>
    <section ref={stageRef} className={`home-stage stage-${stage}`} aria-label="科研知识库神经图谱">
      <div className="stage-bg"/>
      <NetworkCanvas graph={graph} layout={layout} live={live} reduced={reduced}/>
      <Scene graph={graph} items={stage === 'hub' ? [] : items} sel={sel} live={live} media={media} onModule={selectModule} onItem={id => setFocus({mod, sel: id})}/>
      <div className="hub-copy" aria-hidden={stage !== 'hub'}><p className="eyebrow">科研知识库 <span>RESEARCH WIKI</span></p><h1>让每一条链接，<br/>双向生长。</h1><p className="hub-en">Every link grows both ways.</p><p className="hub-meta">5 个模块 <em>modules</em> · {graph.nodes.length} 条笔记 <em>notes</em> · {graph.links.length} 条连线 <em>links</em></p><p className="hub-hint">点击水母，展开模块 <em>Tap a jellyfish to expand</em></p></div>
      {stage !== 'hub' && <nav className="crumbs" aria-label="图谱路径"><button className="crumb-back" aria-label="返回上一层" onClick={() => setFocus(sel ? {mod, sel: null} : {mod: null, sel: null})}><Icon name="back" size={16}/></button><button onClick={() => setFocus({mod: null, sel: null})}>知识库 <em>Core</em></button><span>/</span><button onClick={() => setFocus({mod, sel: null})}>{category?.title}<em>{category?.en}</em></button>{node && <><span>/</span><b>{node.title}</b></>}</nav>}
      <div className="stage-tools glass" role="toolbar" aria-label="动画与刷新"><button onClick={replay} title="重播开场"><Icon name="replay" size={15}/>重播</button><button onClick={() => setPaused(!paused)} aria-pressed={paused}><Icon name={paused ? 'play' : 'pause'} size={15}/>{paused ? '继续' : '暂停'}</button><button onClick={onRefresh} title="重新读取本地笔记"><Icon name="replay" size={15}/>刷新</button></div>
      {stage === 'hub' && <div className="legend glass" aria-label="五类笔记"><h3>模块 <em>Modules</em></h3>{MODULES.map(m => <div key={m.id}><i style={{'--kc': m.color}}/>{m.title}<em>{m.en}</em><b>{graph.nodes.filter(n => n.kind === m.id).length}</b></div>)}<p className="quiet">连线 = 已有页面引用</p></div>}
      {stage === 'hub' && <div className="dock"><div className="dock-panel glass"><div className="dock-kpis">{[['正式笔记', 'Notes', graph.nodes.length], ['页面连线', 'Links', graph.links.length], ['双向引用', 'Mutual', graph.links.filter(l => l.both).length], ['未解析引用', 'Unresolved', graph.unresolved]].map(([title, en, count]) => <div key={en}><span>{title}<em>{en}</em></span><strong>{count}</strong></div>)}</div><p className="neural-source">本地 Markdown · 仅辅助阅读 · 业务操作沿用网页 / CLI</p></div></div>}
      {mod && <div className="neural-pagination glass"><input aria-label="筛选当前模块标题或路径" placeholder="筛选笔记 / Filter notes" value={query} onChange={e => {setQuery(e.target.value); setPage(0);}}/><button aria-label="上一页" disabled={!safePage} onClick={() => {setPage(safePage - 1); setFocus({mod, sel: null});}}>←</button><span>{allItems.length ? safePage * PAGE_SIZE + 1 : 0}–{Math.min((safePage + 1) * PAGE_SIZE, allItems.length)} / {allItems.length}</span><button aria-label="下一页" disabled={safePage >= pages - 1} onClick={() => {setPage(safePage + 1); setFocus({mod, sel: null});}}>→</button></div>}
      {mod && !allItems.length && <p className="module-hint">当前模块没有匹配的正式笔记 <em>No matching notes</em></p>}
      {node && <Detail node={node} graph={graph} onGo={go} onOpen={onOpen} onClose={() => setFocus({mod, sel: null})}/>}
      {error && <p className="neural-error" role="alert">刷新失败，保留上次图谱：{error}</p>}
    </section>
  </div>;
}
