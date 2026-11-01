import { useEffect, useMemo, useRef, useState } from 'react';
import { api, CurationInventory, CurationItem, safeUrl, VisualDecision } from '../api';
import type { AppData } from '../App';
import { pageLink } from '../nav';
import { matchesCatalog } from './SourcesView';

const labels: Record<VisualDecision, string> = { pending: '待筛选', kept: '已保留', removed: '已移除', later: '稍后决定' };
const choices: [VisualDecision, string][] = [['kept', '保留'], ['removed', '移除'], ['later', '稍后决定']];

export function reviewItems(items: CurationItem[], source: string, state: string, query: string, chart: string) {
  return items.filter(i => (!source || i.source_id === source) && (state === 'all' || i.decision === state)
    && (!chart || i.chart_types.includes(chart)) && matchesCatalog(i, query, 'FigureYa'));
}

export function Picture({ item, index, eager = false }: { item: CurationItem; index: number; eager?: boolean }) {
  const [failed, setFailed] = useState(false);
  const image = item.images[index];
  const url = image?.url.startsWith('/api/figureya/image?') ? image.url : safeUrl(image?.url);
  useEffect(() => setFailed(false), [url]);
  return url && !failed
    ? <img src={url} alt={`${item.title} 绘图参考，${index + 1}/${item.images.length}`} loading={eager ? 'eager' : 'lazy'} onError={() => setFailed(true)} />
    : <span className="review-no-image">{failed ? '图片加载失败' : '此版本缺少参考图'}<small>{failed ? '可尝试切换其他图片或刷新页面' : '保留此条目，待补充真实输出后判断'}</small></span>;
}

function ImageViewer({ item, close, busy, decide }: {
  item: CurationItem; close: () => void; busy: boolean; decide: (ids: string[], state: VisualDecision) => Promise<void>;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => element?.close();
  }, []);
  return <dialog className="review-dialog" ref={dialog} aria-labelledby="review-image-title" onCancel={close}
    onClick={e => { if (e.target === e.currentTarget) close(); }}>
    <header><div><h2 id="review-image-title">{item.title}</h2><p className="small muted">{item.id}</p></div>
      <button autoFocus className="ghost" onClick={close}>关闭</button></header>
    <div className="review-large-image"><Picture key={`${item.id}/${index}`} item={item} index={index} eager /></div>
    <div className="review-image-nav">
      <button className="ghost" disabled={index === 0} onClick={() => setIndex(i => i - 1)}>上一张</button>
      <span>{item.images.length ? `${index + 1} / ${item.images.length}　${item.images[index]?.name}` : '暂无图片'}</span>
      <button className="ghost" disabled={index >= item.images.length - 1} onClick={() => setIndex(i => i + 1)}>下一张</button>
    </div>
    <p className="small muted">{item.images[index]?.label} · 仅用于判断样式，不代表本机运行或科学有效性验证。</p>
    <div className="review-actions">{choices.map(([state, label]) => <button key={state} disabled={busy} aria-pressed={item.decision === state}
      className={state === 'removed' ? 'ghost danger' : 'ghost'} onClick={() => void decide([item.id], state)}>{label}</button>)}
      {item.decision !== 'pending' && <button className="ghost" disabled={busy} onClick={() => void decide([item.id], 'pending')}>恢复待筛选</button>}</div>
  </dialog>;
}

export function FigureYaReview({ data }: { data: AppData }) {
  const [inventory, setInventory] = useState<CurationInventory | null>(null);
  const [source, setSource] = useState('figureya');
  const [state, setState] = useState('all');
  const [query, setQuery] = useState('');
  const [chart, setChart] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [opened, setOpened] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const saving = useRef(false);
  const refresh = () => api.figureyaCuration().then(setInventory);
  useEffect(() => {
    let active = true;
    api.figureyaCuration().then(value => { if (active) setInventory(value); })
      .catch((failure: Error) => { if (active) setError(failure.message); });
    return () => { active = false; };
  }, []);
  const items = inventory?.items ?? [];
  const sourceItems = items.filter(i => i.source_id === source);
  const counts = Object.fromEntries(Object.keys(labels).map(s => [s, sourceItems.filter(i => i.decision === s).length]));
  const shown = useMemo(() => reviewItems(items, source, state, query, chart), [inventory, source, state, query, chart]);
  const chartTypes = [...new Set(sourceItems.flatMap(i => i.chart_types))].sort();
  const sources = [...new Set(items.map(i => i.source_id))].sort((a, b) => a === 'figureya' ? -1 : b === 'figureya' ? 1 : a.localeCompare(b));
  const viewing = items.find(i => i.id === opened);
  const toggle = (id: string) => setSelected(previous => { const next = new Set(previous); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  const changeFilter = (fn: () => void) => { fn(); setSelected(new Set()); };
  async function decide(ids: string[], decision: VisualDecision) {
    if (!inventory || saving.current) return;
    saving.current = true; setBusy(true); setError(''); setNotice('正在保存…');
    try {
      const saved = await api.figureyaDecide(ids, decision, inventory.revision);
      setInventory(previous => previous && ({ revision: saved.revision,
        items: previous.items.map(i => saved.decisions[i.id] ? { ...i, decision: saved.decisions[i.id] } : i) }));
      setSelected(new Set());
      setNotice(`已保存 ${ids.length} 项：${labels[decision]}。`);
      void data.reload();
    } catch (failure) {
      setError((failure as Error).message); setNotice('本次操作未保存，请核对记录后重试。');
      await refresh().catch(() => undefined);
    } finally { saving.current = false; setBusy(false); }
  }
  return <section className="figureya-review">
    <header className="hero slim"><div className="hero-text"><h1>看图，留下合适的样式。</h1>
      <p className="lede">FigureYa 全模块筛选。点击图片放大，一个模块有多张图时可逐张查看。</p>
      <p className="small muted">移除后退出默认图库、检索和推荐，可随时恢复。原始材料与已有运行记录保留。</p></div></header>
    <div className="review-toolbar">
      <div className="review-filters">
        <label>来源版本<select aria-label="筛选来源版本" value={source} disabled={busy} onChange={e => changeFilter(() => { setSource(e.target.value); setChart(''); })}>
          {sources.map(s => <option key={s} value={s}>{s === 'figureya' ? '原来源' : '压缩包增量'} · {items.filter(i => i.source_id === s).length} 个模块</option>)}
        </select></label>
        <label className="review-search">查找模块<input aria-label="搜索待筛选模块" type="search" placeholder="图型、关键词或模块编号" value={query} disabled={busy} onChange={e => changeFilter(() => setQuery(e.target.value))} /></label>
        <label>图型<select aria-label="筛选图型" value={chart} disabled={busy} onChange={e => changeFilter(() => setChart(e.target.value))}>
          <option value="">全部图型</option>{chartTypes.map(c => <option key={c} value={c}>{c}</option>)}
        </select></label>
      </div>
      <div className="review-tabs" role="group" aria-label="筛选进度">
        <button aria-pressed={state === 'all'} disabled={busy} onClick={() => changeFilter(() => setState('all'))}>全部 {sourceItems.length}</button>
        {(Object.entries(labels) as [VisualDecision, string][]).map(([key, label]) => <button key={key} disabled={busy} aria-pressed={state === key}
          onClick={() => changeFilter(() => setState(key))}>{label} {counts[key]}</button>)}
      </div>
      <div className="review-progress"><progress aria-label="已处理筛选进度" max={sourceItems.length || 1} value={counts.kept + counts.removed || 0} />
        <span>{counts.kept + counts.removed || 0} / {sourceItems.length} 已决定 · 当前显示 {shown.length} 项</span>
        <span role="status">{notice || '选择会自动保存到本机 Wiki'}</span></div>
      <div className="review-batch"><label><input type="checkbox" aria-label="全选当前结果" disabled={busy || !shown.length}
        checked={shown.length > 0 && shown.every(i => selected.has(i.id))} onChange={e => setSelected(e.target.checked ? new Set(shown.map(i => i.id)) : new Set())} /> 全选当前结果</label>
        <span>已选 {selected.size} 项</span>
        {choices.map(([key, label]) => <button key={key} className={key === 'removed' ? 'ghost danger' : 'ghost'} disabled={busy || !selected.size}
          onClick={() => void decide([...selected], key)}>批量{label}</button>)}
        <button className="ghost" disabled={busy || !selected.size} onClick={() => void decide([...selected], 'pending')}>恢复待筛选</button>
      </div>
    </div>
    {error && <p className="notice error" role="alert">{error} <button onClick={() => void refresh().then(() => setError('')).catch(f => setError(f.message))}>重新加载</button></p>}
    {!inventory ? <p role="status">正在读取全部模块和本地参考图…</p> : <div className="review-grid">{shown.map((item, number) =>
      <article key={item.id} className={`review-card decision-${item.decision}`}>
        <div className="review-card-top"><label><input type="checkbox" checked={selected.has(item.id)} disabled={busy} onChange={() => toggle(item.id)} aria-label={`选择 ${item.id}`} /> {number + 1}</label>
          <span className={`review-decision decision-${item.decision}`}>{labels[item.decision]}</span></div>
        <button className="review-image" aria-label={`放大 ${item.id} 的参考图`} onClick={() => setOpened(item.id)}>
          <Picture item={item} index={0} /><span className="review-image-hint">{item.images.length ? `放大查看 · ${item.images.length} 张图` : '缺少参考图'}</span></button>
        <div className="review-card-body"><h2>{item.title}</h2><p className="review-id">{item.id.split(':')[1]}</p>
          <p className="review-caption">{item.images[0]?.label ?? '暂无参考图'} · {item.recipes.length ? '已收录配方' : '来源目录项'}</p>
          <div className="review-actions">{choices.map(([key, label]) => <button key={key} className={key === 'removed' ? 'ghost danger' : 'ghost'} disabled={busy}
            aria-pressed={item.decision === key} onClick={() => void decide([item.id], key)}>{label}</button>)}
            {item.decision !== 'pending' && <button className="ghost review-restore" disabled={busy} onClick={() => void decide([item.id], 'pending')}>恢复</button>}</div>
          <details><summary>用途与来源</summary><p>{item.summary || item.scenario || '详见来源页。'}</p>
            <a {...pageLink(item.page)}>来源说明</a>{item.recipes.map(r => <p key={r.id}><a {...pageLink(r.page)}>{r.title} · 配方</a></p>)}
            <p className="small muted">保留只记录样式偏好，不改变 ready 或运行验证状态。</p></details>
        </div>
      </article>)}</div>}
    {inventory && !shown.length && <p className="notice">没有符合条件的模块，可切换到“全部”或清空搜索。</p>}
    {viewing && <ImageViewer key={viewing.id} item={viewing} close={() => setOpened(null)} busy={busy} decide={decide} />}
  </section>;
}
