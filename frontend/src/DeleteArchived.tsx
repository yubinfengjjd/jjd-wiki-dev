import { useState } from 'react';
import { api, DeletePlan, ItemMeta, KIND_OF } from './api';

export function DeleteArchived({ meta, onDeleted }: { meta: ItemMeta; onDeleted: () => Promise<void> }) {
  const [plan, setPlan] = useState<DeletePlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState('');
  if (meta.status !== 'archived') return null;
  const inspect = async () => {
    setBusy(true); setError(''); setChecked(false);
    try { setPlan(await api.deletePlan(KIND_OF[meta.type], meta.id)); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  const remove = async () => {
    if (!plan || !checked) return;
    setBusy(true); setError('');
    try {
      await api.deleteArchived(KIND_OF[meta.type], meta.id, plan.revision);
    } catch (e) {
      setError((e as Error).message); setChecked(false); setBusy(false);
      return;
    }
    // Deletion is committed and irreversible from here; a refresh failure must not read as a failed delete.
    setPlan(null);
    try { await onDeleted(); }
    catch (e) { setError(`已永久删除，但刷新页面失败：${(e as Error).message}。请刷新浏览器。`); }
    finally { setBusy(false); }
  };
  const relations = plan?.figure_relations_removed ?? 0;
  const layouts = plan?.layout_files_updated ?? [];
  return <div className="delete-archived">
    <button className="ghost danger" disabled={busy} onClick={inspect}>删除</button>
    {error && !plan && <p role="alert" className="notice error">{error}</p>}
    {plan && <div className="delete-backdrop">
      <section role="dialog" aria-modal="true" aria-labelledby={`delete-${meta.id}`} className="sheet delete-dialog">
        <h2 id={`delete-${meta.id}`}>永久删除归档条目</h2>
        <p>{plan.title}</p>
        <p>将删除 Wiki 页面和 {plan.asset_files} 个专属资产文件，自动清理以下 {plan.affected.length} 个页面中的关联，并保存变更记录。原始画廊保留。</p>
        {plan.affected.length > 0 && <ul>{plan.affected.map((p) => <li key={p.path}>{p.title}
          {p.figure_relations_removed ? `（移除 ${p.figure_relations_removed} 条方法配图关系）` : ''}</li>)}</ul>}
        {relations > 0 && <p>共移除 {relations} 条方法配图关系。</p>}
        {layouts.length > 0 && <>
          <p>以下版式的 layout.json 会被改写；若删后不剩任何 panel 则删除该文件，相应版式从“可用”退回“待模板化”：</p>
          <ul>{layouts.map((path) => <li key={path}><code>{path}</code></li>)}</ul>
        </>}
        <label className="check"><input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} disabled={busy} />我确认永久删除，无法从界面恢复</label>
        {error && <p role="alert" className="notice error">{error}</p>}
        <div className="panel-row">
          <button className="danger" disabled={!checked || busy} onClick={remove}>{busy ? '处理中…' : '确认永久删除'}</button>
          <button className="ghost" disabled={busy} onClick={() => setPlan(null)}>取消</button>
        </div>
      </section>
    </div>}
  </div>;
}
