import { useEffect, useState } from 'react';
import { api, DeletePlan } from './api';

export interface DeleteTemplateModalProps {
  templateId: string;
  templateTitle: string;
  templatePath: string;
  onClose: () => void;
  onDeleted: (result: DeletePlan & { deleted: boolean; audit: string }) => void;
}

export function DeleteTemplateModal({
  templateId,
  templateTitle,
  templatePath,
  onClose,
  onDeleted,
}: DeleteTemplateModalProps) {
  const [plan, setPlan] = useState<DeletePlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    setChecked(false);
    api.deletePlan('templates', templateId, true)
      .then((res) => {
        if (active) setPlan(res);
      })
      .catch((err: Error) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [templateId]);

  const confirmDelete = async () => {
    if (!plan || !checked) return;
    setBusy(true);
    setError('');
    try {
      const result = await api.deleteArchived('templates', templateId, plan.revision, true);
      onDeleted(result);
    } catch (err) {
      setError((err as Error).message);
      setChecked(false);
      setBusy(false);
    }
  };

  const relations = plan?.figure_relations_removed ?? 0;
  const layouts = plan?.layout_files_updated ?? [];

  return (
    <div className="delete-backdrop" onClick={(e) => { if (e.target === e.currentTarget && !busy) onClose(); }}>
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby={`delete-template-${templateId}`}
        className="sheet delete-dialog"
      >
        <h2 id={`delete-template-${templateId}`}>安全删除绘图模版</h2>
        <p className="delete-modal-meta">
          <strong>{templateTitle}</strong> <code>{templatePath}</code>
        </p>

        {loading && <p className="notice small" role="status">正在扫描 Wiki 引用与关联影响…</p>}
        {error && <p role="alert" className="notice error">{error}</p>}

        {plan && (
          <>
            {plan.slot_default_warning && (
              <div className="slot-default-warning notice" role="note">
                <strong>主推默认槽位提示</strong>
                <p className="small">{plan.slot_default_warning.message}</p>
              </div>
            )}

            <p className="small">
              将永久移除 <code>{plan.path}</code> 及 <strong>{plan.asset_files}</strong> 个专属资产文件，
              并自动清理以下 <strong>{plan.affected.length}</strong> 个 Wiki 页面中的引用与关联。
            </p>

            {plan.affected.length > 0 && (
              <ul className="delete-affected-list small">
                {plan.affected.map((p) => (
                  <li key={p.path}>
                    <span>{p.title}</span> <code>{p.path}</code>
                    {p.figure_relations_removed ? `（移除 ${p.figure_relations_removed} 条方法配图关系）` : ''}
                  </li>
                ))}
              </ul>
            )}

            {relations > 0 && (
              <p className="small muted">共移除 {relations} 条方法配图关系。</p>
            )}

            {layouts.length > 0 && (
              <>
                <p className="small">以下关联文件将自动更新：</p>
                <ul className="delete-affected-list small">
                  {layouts.map((path) => <li key={path}><code>{path}</code></li>)}
                </ul>
              </>
            )}

            <p className="small muted">
              原始画廊与来源数据保留不变；本次删除会生成审计记录并提交至 Git 历史（可通过 <code>git revert</code> 恢复）。
            </p>

            <label className="check">
              <input
                type="checkbox"
                checked={checked}
                onChange={(e) => setChecked(e.target.checked)}
                disabled={busy}
              />
              我已核对影响范围，确认永久删除该绘图模版
            </label>
          </>
        )}

        <div className="panel-row">
          {plan && (
            <button
              type="button"
              className="danger"
              disabled={!checked || busy}
              onClick={() => void confirmDelete()}
            >
              {busy ? '正在删除…' : '确认删除模版'}
            </button>
          )}
          <button type="button" className="ghost" disabled={busy} onClick={onClose}>
            取消
          </button>
        </div>
      </section>
    </div>
  );
}
