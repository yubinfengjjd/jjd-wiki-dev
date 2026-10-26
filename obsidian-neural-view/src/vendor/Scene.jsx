// Adapted from upstream Home.jsx; see PROVENANCE.md.
import React, {useEffect, useLayoutEffect, useMemo, useRef, useState, useCallback, useId} from 'react';
import {MODULES, KINDS} from '../graph.mjs';
import {Icon} from './icons';
import {T} from './theme';

const FLIP = {layouts: 1, templates: -1, methods: -1, interfaces: -1, projects: 1};
export const MOD_STYLE = Object.fromEntries(Object.entries(T.modules).map(([id, m]) => [id, {...m, flip: FLIP[id]}]));

export const split = n => ({out: n.out - n.mutual, back: n.in - n.mutual, both: n.mutual});
const fmt = v => v == null ? '—' : Number(v).toLocaleString('zh-CN');

export function moduleItems(graph, modId) {
  const m = MODULES.find(x => x.id === modId);
  if (!m) return [];
  const list = graph.nodes.filter(n => n.kind === m.kind);
  if (m.kind === 'post') list.sort((a, b) => String(b.date).localeCompare(String(a.date)));
  if (m.kind === 'concept') list.sort((a, b) => b.in - a.in);
  return list;
}

function moduleSummary(graph, m) {
  const items = moduleItems(graph, m.id);
  return {count: items.length, sub: [items.reduce((s,n)=>s+n.out,0), '出链', 'explicit links']};
}
function itemMeta(n) {
  return [['出链', 'Out', n.out], ['入链', 'In', n.in]];
}

// —— 布局目标 ——
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export function targets(L, t) {
  const {w: W, h: H} = L.size, st = L.stage, narrow = W < 760;
  const swim = L.reduced ? 0 : 1;
  const res = {orb: {}, jelly: {}, fan: null};
  if (st === 'hub') {
    const s = narrow ? clamp(W * .56, 180, 280) : clamp(Math.min(W, H) * .5, 250, 440);
    const cy = narrow ? H * .47 : H * .53;
    res.orb = {x: W / 2, y: cy, s};
    const rx = narrow ? W * .36 : Math.min(W * .36, 540), ry = narrow ? H * .21 : Math.min(H * .32, 262);
    MODULES.forEach((m, i) => {
      const a = (m.angle + swim * 7 * Math.sin(t * .17 + i * 1.7)) * Math.PI / 180;
      const r = 1 + swim * .04 * Math.sin(t * .23 + i);
      res.jelly[m.id] = {x: W / 2 + Math.cos(a) * rx * r, y: cy + Math.sin(a) * ry * r + swim * 9 * Math.sin(t * .9 + i * 2.1), s: narrow ? 92 : clamp(W * .12, 120, 184), o: 1, tilt: swim * 6 * Math.sin(t * .6 + i)};
    });
  } else if (narrow) {
    res.orb = {x: 40, y: 156, s: 86};
    MODULES.forEach((m, i) => {
      const sel = m.id === L.mod, k = slotOf(L.mod, m.id);
      res.jelly[m.id] = {x: 104 + k * (W - 136) / 4, y: 152 + swim * 4 * Math.sin(t * .9 + i * 2), s: sel ? 76 : 54, o: sel ? 1 : .55, tilt: swim * 3 * Math.sin(t * .6 + i)};
    });
    const n = L.items.length, gap = clamp((H - 330) / Math.max(n - 1, 1), 22, 54);
    res.fan = {x: 34, y0: 286, gap};
  } else {
    const ox = Math.max(124, W * .09), cy = H * .53;
    res.orb = {x: ox, y: cy, s: 178};
    const colX = ox + 158, gap = Math.min(122, (H - 150) / 5);
    MODULES.forEach((m, i) => {
      const sel = m.id === L.mod, k = slotOf(L.mod, m.id);
      res.jelly[m.id] = {x: colX + (sel ? 16 : 0), y: cy + (k - 2) * gap + swim * 5 * Math.sin(t * .9 + i * 2), s: sel ? 128 : 92, o: sel ? 1 : .6, tilt: swim * 3 * Math.sin(t * .6 + i)};
    });
    // 伞状条目以右侧分析栏为基准排在它左边约 90px 处（条目最宽约 270px），触须拉长、画面左右均衡；
    // 模块层和打开笔记后位置相同，右侧栏滑入时伞不跳动
    const panelLeft = W - clamp(W * .33, 380, 470) - 44;
    const n = L.items.length;
    const span = Math.min(H - 130, Math.max(0, n - 1) * 54);
    const originX = colX + 16 + 128 * .5 + 10 + 168;
    res.fan = {x: Math.min(Math.max(panelLeft - 270 - 90, originX + 60), panelLeft - 280), y0: cy - span / 2, gap: n > 1 ? span / (n - 1) : 0};
  }
  return res;
}

// 选中的模块排在列的正中间（第 2 格），其余模块按原顺序分列上下，触须从中间向上下对称展开。
function slotOf(selId, id) {
  const others = MODULES.filter(m => m.id !== selId).map(m => m.id);
  const order = [others[0], others[1], selId, others[2], others[3]];
  const k = order.indexOf(id);
  return k < 0 ? MODULES.findIndex(m => m.id === id) : k;
}

function spring(st, target, dt, k = 62) {
  const c = 2 * Math.sqrt(k);
  st.v += (-k * (st.x - target) - c * st.v) * dt;
  st.x += st.v * dt;
  return st.x;
}
export const sp = x => ({x, v: 0});
// 光球边缘向外飘散的光点（光球本地坐标，画布 1012×1012，中心 506）
const DUST = Array.from({length: 110}, (_, i) => ({a: i * 2.39996, v: .035 + (i * 37 % 100) / 100 * .06, o: (i * .618034) % 1, w: (i % 2 ? 1 : -1) * (.15 + (i % 7) * .05), s: .7 + (i % 5) * .32, b: .45 + (i % 3) * .25, c: T.dust[i % T.dust.length]}));
// 光球与水母的视频逐帧画到 <canvas> 上显示：部分内置 / 嵌入式浏览器不合成 <video> 画面（解码正常但页面上是空的），
// 画布在所有浏览器里都能显示。视频本身透明地留在原位负责播放；未加载好时先画封面图。
const posterCache = new Map();
const posterOf = url => { if (!posterCache.has(url)) { const img = new Image(); img.src = url; posterCache.set(url, img); } return posterCache.get(url); };
function paintVideo(pair) {
  const {video, canvas} = pair;
  if (!video || !canvas) return;
  const cw = canvas.clientWidth, ch = canvas.clientHeight;
  if (!cw || !ch) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2), W = Math.round(cw * dpr), H = Math.round(ch * dpr);
  const resized = canvas.width !== W || canvas.height !== H;
  if (resized) { canvas.width = W; canvas.height = H; }
  const ready = video.readyState >= 2 && video.videoWidth;
  const src = ready ? video : posterOf(video.poster);
  const sw0 = ready ? video.videoWidth : src.naturalWidth, sh0 = ready ? video.videoHeight : src.naturalHeight;
  if (!sw0 || !sh0) return;
  const stamp = ready ? video.currentTime : -1;
  if (!resized && stamp === pair.stamp && ready === pair.ready) return;
  pair.stamp = stamp; pair.ready = ready;
  // 等同 object-fit: cover
  const k = Math.max(W / sw0, H / sh0), sw = W / k, sh = H / k;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, W, H);
  ctx.drawImage(src, (sw0 - sw) / 2, (sh0 - sh) / 2, sw, sh, 0, 0, W, H);
}

const bez = (p0, p1, p2, p3, u) => { const m = 1 - u; return m * m * m * p0 + 3 * m * m * u * p1 + 3 * m * u * u * p2 + u * u * u * p3; };

export function Scene({graph, items, onModule, onItem, live, sel, media}) {
  const svgId = useId().replace(/[^a-zA-Z0-9-]/g, '');
  const dustRef = useRef(null);
  const orbRef = useRef(null), jellyRefs = useRef({}), innerRefs = useRef({}), labelRefs = useRef({}), threadRefs = useRef({}), pulseRefs = useRef({});
  const itemRefs = useRef([]), fanRefs = useRef([]), fanPulseRefs = useRef([]);
  const vids = useRef({});
  const vidRef = (id, part) => el => { (vids.current[id] ||= {})[part] = el; };
  const summaries = useMemo(() => Object.fromEntries(MODULES.map(m => [m.id, moduleSummary(graph, m)])), [graph]);

  useLayoutEffect(() => { live.current.itemState = items.map(() => null); live.current.fanStart = performance.now(); }, [items, live]);

  useEffect(() => {
    let raf, last = performance.now();
    const S = live.current.springs;
    const step = now => {
      const L = live.current;
      // rAF 给的是帧开始时间，可能早于上面记录的 last；负的 dt 会让后续计算出现 NaN，所以限制为 ≥ 0
      const dt = Math.max(0, Math.min(1 / 30, (now - last) / 1000)); last = Math.max(last, now);
      if (L.hidden || document.hidden) return;
      if (!L.paused) L.time += dt;
      const t = L.time, since = (now - L.t0) / 1000;
      const T = targets(L, t);
      const intro = L.stage === 'hub' && !L.reduced;
      // 光球
      const orbS = intro && since < .15 ? T.orb.s * .35 : T.orb.s;
      const ox = spring(S.orb.x, T.orb.x, dt), oy = spring(S.orb.y, T.orb.y, dt), os = spring(S.orb.s, orbS, dt, 40), oo = spring(S.orb.o, intro && since < .1 ? 0 : 1, dt, 30);
      L.orb = {x: ox, y: oy, s: os};
      if (orbRef.current) { orbRef.current.style.transform = `translate3d(${ox - os / 2}px,${oy - os / 2}px,0) scale(${os / 460})`; orbRef.current.style.opacity = clamp(oo, 0, 1); }
      const dust = dustRef.current;
      if (dust) {
        const di = clamp(spring(S.dust, L.stage === 'hub' ? .3 : 1, dt, 18), 0, 1);
        const ctx = dust.getContext('2d');
        ctx.clearRect(0, 0, 1012, 1012);
        if (!L.reduced && di > .02) {
          const sc = Math.max(os / 460, .2);
          ctx.globalCompositeOperation = 'lighter';
          for (const p of DUST) {
            const ph = ((t * p.v + p.o) % 1 + 1) % 1, r = 150 + ph * 340, a = p.a + ph * p.w;
            const x = 506 + Math.cos(a) * r, y = 506 + Math.sin(a) * r * .96;
            const al = di * Math.pow(Math.max(0, Math.sin(ph * Math.PI)), 1.3) * p.b, rad = p.s / sc * 2.2;
            const g = ctx.createRadialGradient(x, y, 0, x, y, rad);
            g.addColorStop(0, `rgba(${p.c},${al})`); g.addColorStop(1, `rgba(${p.c},0)`);
            ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, rad, 0, 7); ctx.fill();
          }
        }
      }
      // 水母
      MODULES.forEach((m, i) => {
        const j = S.jelly[m.id], tg = T.jelly[m.id];
        const gated = intro && since < 1 + i * .17;
        const x = spring(j.x, gated ? ox : tg.x, dt), y = spring(j.y, gated ? oy : tg.y, dt), s = spring(j.s, gated ? 24 : tg.s, dt), o = spring(j.o, gated ? 0 : tg.o, dt, 40);
        const lo = spring(j.lo, intro && since < 2 + i * .1 ? 0 : tg.o, dt, 40);
        j.cur = {x, y, s};
        const el = jellyRefs.current[m.id], inner = innerRefs.current[m.id], lab = labelRefs.current[m.id];
        if (el) { el.style.transform = `translate3d(${x - s / 2}px,${y - s * .375}px,0) scale(${s / 200})`; el.style.opacity = clamp(o, 0, 1); }
        if (inner) inner.style.transform = `rotate(${tg.tilt}deg) scaleX(${MOD_STYLE[m.id].flip})`;
        if (lab) {
          const lw = lab.offsetWidth, lh = lab.offsetHeight;
          const hub = L.stage === 'hub', narrow = L.size.w < 760;
          // 侧列时标签放在水母右边缘之外再空 10px，触须不压标签
          const lx = hub ? x - lw / 2 : narrow ? x - lw / 2 : x + s * .5 + 10;
          const ly = hub ? y + s * .36 : narrow ? y + s * .36 : y - lh / 2;
          lab.style.transform = `translate3d(${lx}px,${ly}px,0)`;
          lab.style.opacity = clamp(narrow && !hub && m.id !== L.mod ? 0 : lo, 0, 1);
          j.label = {x: lx, y: ly, w: lw, h: lh};
        }
        // 光球 → 水母：神经丝与往返脉冲
        const g = threadRefs.current[m.id];
        if (g) {
          let x1, y1, x2, y2, c1x, c1y, c2x, c2y;
          if (L.stage === 'hub') {
            const dx = x - ox, dy = y - oy, d = Math.hypot(dx, dy) || 1, ux = dx / d, uy = dy / d;
            x1 = ox + ux * os * .2; y1 = oy + uy * os * .2; x2 = x - ux * s * .22; y2 = y - uy * s * .1;
            const bend = 26 * Math.sin(t * .5 + i);
            c1x = x1 + dx * .35 - uy * bend; c1y = y1 + dy * .35 + ux * bend; c2x = x1 + dx * .7 + uy * bend; c2y = y1 + dy * .7 - ux * bend;
          } else {
            x1 = ox + os * .3; y1 = oy; x2 = x - s * .34; y2 = y;
            const dx = x2 - x1; c1x = x1 + dx * .55; c1y = y1; c2x = x2 - dx * .55; c2y = y2;
          }
          const d = `M${x1},${y1} C${c1x},${c1y} ${c2x},${c2y} ${x2},${y2}`;
          const active = m.id === L.mod || m.kind === L.hover;
          g.glow.setAttribute('d', d); g.core.setAttribute('d', d);
          const vis = clamp(o, 0, 1) * (L.stage === 'hub' ? 1 : active ? 1 : .45);
          g.glow.style.opacity = vis * (active ? .9 : .45); g.core.style.opacity = vis;
          const pulses = pulseRefs.current[m.id] || [];
          pulses.forEach((c, k) => {
            if (!c) return;
            const inbound = k === 2;
            let u = ((t * (inbound ? .23 : .31) + k * .5 + i * .17) % 1);
            if (inbound) u = 1 - u;
            c.setAttribute('cx', bez(x1, c1x, c2x, x2, u)); c.setAttribute('cy', bez(y1, c1y, c2y, y2, u));
            c.style.opacity = L.reduced || L.paused ? 0 : vis * Math.sin(u * Math.PI);
          });
        }
      });
      // 选中模块 → 多篇笔记（触须式扇形展开）
      const sj = L.mod && S.jelly[L.mod];
      if (T.fan && sj?.label) {
        const narrow = L.size.w < 760;
        const ox2 = narrow ? sj.label.x + sj.label.w / 2 : sj.label.x + sj.label.w + 6, oy2 = narrow ? sj.label.y + sj.label.h + 4 : sj.cur.y;
        items.forEach((n, i) => {
          if (!L.itemState[i]) L.itemState[i] = {x: sp(ox2), y: sp(oy2), o: sp(0)};
          const st = L.itemState[i];
          // 触须一根一根依次长出（20 条约 1.8 秒），形成伞状开花的节奏
          const ready = L.reduced || now - L.fanStart > 160 + i * Math.min(90, 1800 / Math.max(items.length, 1));
          const tx = T.fan.x, ty = T.fan.y0 + i * T.fan.gap + (L.reduced ? 0 : Math.sin(t * .8 + i * .9) * 2);
          const x = spring(st.x, ready ? tx : ox2, dt, 70), y = spring(st.y, ready ? ty : oy2, dt, 70), o = spring(st.o, ready ? 1 : 0, dt, 50);
          const el = itemRefs.current[i];
          if (el) { el.style.transform = `translate3d(${x}px,${y - 15}px,0)`; el.style.opacity = clamp(o, 0, 1); }
          const p = fanRefs.current[i];
          if (p) {
            const dx = x - ox2, sway = L.reduced ? 0 : Math.sin(t * 1.1 + i * .7) * 7;
            const c1x = ox2 + dx * .5, c1y = oy2 + sway, c2x = x - dx * .45, c2y = y - sway * .5;
            p.setAttribute('d', `M${ox2},${oy2} C${c1x},${c1y} ${c2x},${c2y} ${x},${y}`);
            const on = sel === n.id;
            p.style.opacity = clamp(o, 0, 1) * (sel ? (on ? 1 : .35) : .8);
            p.style.strokeWidth = on ? 1.8 : 1;
            (fanPulseRefs.current[i] || []).forEach((c, k) => {
              if (!c) return;
              let u = (t * (k ? .27 : .36) + i * .13 + k * .5) % 1;
              if (k) u = 1 - u;
              c.setAttribute('cx', bez(ox2, c1x, c2x, x, u)); c.setAttribute('cy', bez(oy2, c1y, c2y, y, u));
              c.style.opacity = L.reduced || L.paused ? 0 : clamp(o, 0, 1) * Math.sin(u * Math.PI) * (sel && !on ? .3 : 1);
            });
          }
        });
      }
      // 光球与水母的视频画面
      for (const pair of Object.values(vids.current)) paintVideo(pair);
    };
    // 每帧先排好下一帧再执行：某一帧出错也不会让光球和水母停住
    let warned = false;
    const frame = now => { raf = requestAnimationFrame(frame); try { step(now); } catch (err) { if (!warned) { warned = true; console.error(err); } } };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [items, live, sel]);

  // 暂停时一并暂停视频
  useEffect(() => {
    const sync = () => Object.values(vids.current).forEach(({video: v}) => { if (!v) return; if (live.current.paused || live.current.hidden || live.current.reduced || document.hidden) v.pause(); else v.play().catch(() => {}); });
    live.current.syncVideo = sync; sync();
    document.addEventListener('visibilitychange', sync);
    return () => { document.removeEventListener('visibilitychange', sync); Object.values(vids.current).forEach(({video}) => video?.pause()); delete live.current.syncVideo; };
  }, [live]);

  const hub = live.current.stage === 'hub';
  return <div className={`scene stage-${live.current.stage}`}>
    <div className="orb" ref={orbRef} aria-hidden="true">
      <div className="orb-halo"/>
      <video className="vsrc" ref={vidRef('orb', 'video')} src={media.orb} poster={media.orbPoster} muted loop playsInline autoPlay preload="auto"/>
      <canvas className="vid" ref={vidRef('orb', 'canvas')}/>
      <canvas className="orb-dust" ref={dustRef} width="1012" height="1012"/>
    </div>
    <svg className="threads" aria-hidden="true">
      <defs>
        <filter id={`${svgId}-thread-blur`} x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3.2"/></filter>
        <radialGradient id={`${svgId}-pulse-out`}><stop offset="0" stopColor={T.pulse.out[0]}/><stop offset=".4" stopColor={T.pulse.out[1]}/><stop offset="1" stopColor={T.pulse.out[1]} stopOpacity="0"/></radialGradient>
        <radialGradient id={`${svgId}-pulse-in`}><stop offset="0" stopColor={T.pulse.in[0]}/><stop offset=".4" stopColor={T.pulse.in[1]}/><stop offset="1" stopColor={T.pulse.in[1]} stopOpacity="0"/></radialGradient>
      </defs>
      {MODULES.map(m => <g key={m.id} style={{color: MOD_STYLE[m.id].color}}>
        <path ref={el => { threadRefs.current[m.id] = {...threadRefs.current[m.id], glow: el}; }} className="thread-glow" filter={`url(#${svgId}-thread-blur)`}/>
        <path ref={el => { threadRefs.current[m.id] = {...threadRefs.current[m.id], core: el}; }} className="thread-core"/>
        {[0, 1, 2].map(k => <circle key={k} r={k === 2 ? 4.5 : 5.5} fill={`url(#${svgId}-${k === 2 ? 'pulse-in' : 'pulse-out'})`} ref={el => { (pulseRefs.current[m.id] ||= [])[k] = el; }}/>)}
      </g>)}
      {items.map((n, i) => <g key={n.id} style={{color: KINDS[n.kind].color}}>
        <path className="fan-thread" ref={el => { fanRefs.current[i] = el; }}/>
        {[0, 1].map(k => <circle key={k} r={k ? 3.5 : 4.5} fill={`url(#${svgId}-${k ? 'pulse-in' : 'pulse-out'})`} ref={el => { (fanPulseRefs.current[i] ||= [])[k] = el; }}/>)}
      </g>)}
    </svg>
    {MODULES.map(m => {
      const sum = summaries[m.id], active = live.current.mod === m.id;
      return <React.Fragment key={m.id}>
        <button className={`jelly ${active ? 'active' : ''}`} ref={el => { jellyRefs.current[m.id] = el; }} onClick={() => onModule(m.id)}
          onPointerEnter={() => { live.current.hover = m.kind; }} onPointerLeave={() => { live.current.hover = null; }}
          aria-label={`${m.title} ${m.en}，${sum.count} 条`}>
          <div className="jelly-inner" ref={el => { innerRefs.current[m.id] = el; }} style={{filter: MOD_STYLE[m.id].filter}}>
            <video className="vsrc" ref={vidRef(m.id, 'video')} src={media.jelly} poster={media.jellyPoster} muted loop playsInline autoPlay preload="auto"
              onLoadedMetadata={e => { e.currentTarget.currentTime = (MODULES.indexOf(m) * 1.37) % 6; }}/>
            <canvas className="vid" ref={vidRef(m.id, 'canvas')}/>
          </div>
        </button>
        <button className={`jelly-label ${active ? 'active' : ''} ${hub ? 'below' : 'side'}`} ref={el => { labelRefs.current[m.id] = el; }} onClick={() => onModule(m.id)} tabIndex={-1}
          onPointerEnter={() => { live.current.hover = m.kind; }} onPointerLeave={() => { live.current.hover = null; }} style={{'--mod': MOD_STYLE[m.id].color}}>
          <span className="jl-icon"><Icon name={m.icon} size={14}/></span>
          <span className="jl-count">{sum.count}</span>
          <span className="jl-name">{m.title}<em>{m.en}</em></span>
          <span className="jl-sub">{sum.sub[0]} {sum.sub[1]} <em>{sum.sub[2]}</em></span>
        </button>
      </React.Fragment>;
    })}
    {items.map((n, i) => {
      const meta = itemMeta(n);
      return <button key={n.id} className={`fan-item ${sel === n.id ? 'active' : ''} kind-${n.kind}`} ref={el => { itemRefs.current[i] = el; }} onClick={() => onItem(n.id)} style={{'--kc': KINDS[n.kind].color}} aria-label={`查看 ${n.title} 的详情`}>
        <span className="fi-dot"/>
        <span className="fi-body">
          <span className="fi-title">{n.short || n.title}</span>
          <span className="fi-meta">{meta.map(([k, en, v], j) => <span key={j} className={k === '↔' ? 'mutual' : ''}>{k}{en && <em>{en}</em>} {v !== '' && <b>{v}</b>}</span>)}</span>
        </span>
      </button>;
    })}
  </div>;
}
