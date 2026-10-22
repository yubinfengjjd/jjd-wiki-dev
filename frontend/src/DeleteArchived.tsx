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
      setPlan(null);
      await onDeleted();
    } catch (e) { setError((e as Error).message); setChecked(false); }
    finally { setBusy(false); }
  };
  return <div className="delete-archived">
    <button className="ghost danger" disabled={busy} onClick={inspect}>删除</button>
    {error && !plan && <p role="alert" className="notice error">{error}</p>}
    {plan && <div className="delete-backdrop">
      <section role="dialog" aria-modal="true" aria-labelledby={`delete-${meta.id}`} className="sheet delete-dialog">
        <h2 id={`delete-${meta.id}`}>永久删除归档条目</h2>
        <p>{plan.title}</p>
        <p>将删除 Wiki 页面和 {plan.asset_files} 个专属资产文件，自动清理以下 {plan.affected.length} 个页面中的关联，并保存变更记录。原始画廊保留。</p>
        {plan.affected.length > 0 && <ul>{plan.affected.map((p) => <li key={p.path}>{p.title}</li>)}</ul>}
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
