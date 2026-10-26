import { useState } from 'react';
import { api, effectiveStatus, galleryFile, ItemMeta, KIND_OF, LayoutMeta, methodNoteLabel, MethodMeta, PageDetail, safeUrl, wikiFile, Workflow } from '../api';
import { StatusBadge } from '../components';
import { DeleteArchived } from '../DeleteArchived';

/** Resolves true only when the write succeeded. */
type Run = (action: () => Promise<PageDetail>) => Promise<boolean>;

interface ActionProps {
  meta: ItemMeta;
  run: Run;
  busy: boolean;
  onDeleted?: () => Promise<void>;
  workflow?: Workflow | null;
}

/** Layout viewer: the replay of the whole figure first once it exists, then the gallery's own images. */
export function LayoutImages({ page, meta }: { page: PageDetail; meta: LayoutMeta }) {
  const files = page.gallery?.files ?? {};
  const views: [string, string][] = [];
  if (meta.status === 'ready') views.push(['按版式回放', wikiFile(`layouts/${meta.id}/preview.png`)]);
  if (files.compare) views.push(['并排对比', galleryFile(meta.gallery_entry, files.compare)]);
  if (files.output_png || files.replica) views.push(['复刻图', galleryFile(meta.gallery_entry, files.output_png || files.replica)]);
  if (files.source_image) views.push(['原图', galleryFile(meta.gallery_entry, files.source_image)]);
  // Kept by label: the tab list changes when the page is archived or restored.
  const [picked, setPicked] = useState('');

  if (views.length === 0) return null;
  const [label, src] = views.find(([l]) => l === picked) ?? views[0];
  return (
    <figure className="viewer">
      <div className="tabs" role="tablist">
        {views.map(([l]) => (
          <button key={l} role="tab" aria-selected={l === label} className={l === label ? 'active' : ''} onClick={() => setPicked(l)}>
            {l}
          </button>
        ))}
      </div>
      <a className="plate" style={{ viewTransitionName: 'plate' }} href={src} target="_blank" rel="noreferrer">
        <img src={src} alt={label} />
      </a>
    </figure>
  );
}

/** A reason form shared by "reject a sign-off" and "return a method". */
function ReasonForm({ label, submit, cancel, busy }: { label: string; submit: (reason: string) => Promise<void>; cancel: () => void; busy: boolean }) {
  const [reason, setReason] = useState('');
  return (
    <form
      className="stack"
      onSubmit={(e) => {
        e.preventDefault();
        submit(reason.trim());
      }}
    >
      <label htmlFor="reason">{label}</label>
      <textarea id="reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} required />
      <div className="panel-row">
        <button className="primary" disabled={busy || !reason.trim()}>确认</button>
        <button type="button" className="ghost" onClick={cancel}>取消</button>
      </div>
    </form>
  );
}

export function ItemActions({ meta, run, busy, onDeleted, workflow }: ActionProps) {
  const [reasoning, setReasoning] = useState(false);
  const kind = KIND_OF[meta.type];
  const withReason = (send: (reason: string) => Promise<PageDetail>) => (reason: string) =>
    run(() => send(reason)).then((ok) => { if (ok) setReasoning(false); });

  return (
    <div className="panel">
      <div className="panel-row">
        <StatusBadge status={effectiveStatus(meta, workflow ?? null)} label={meta.type === 'method' ? methodNoteLabel(meta, workflow) : workflow?.label} />
        <button className="ghost" disabled={busy} onClick={() => run(() => api.favorite(kind, meta.id, !meta.favorite))} aria-pressed={meta.favorite}>
          {meta.favorite ? '★ 已收藏' : '☆ 收藏'}
        </button>
      </div>

      {reasoning ? (
        meta.type === 'layout' ? (
          <ReasonForm label={meta.status === 'pending_signoff' ? '退回理由' : '撤回签核的理由'} submit={withReason((r) => api.reject(meta.id, r))} cancel={() => setReasoning(false)} busy={busy} />
        ) : (
          <ReasonForm label="退回理由（agent 会据此修改）" submit={withReason((r) => api.returnMethod(meta.id, r))} cancel={() => setReasoning(false)} busy={busy} />
        )
      ) : (
        <>
          {meta.type === 'layout' && meta.status === 'pending_signoff' && (
            <div className="panel-row">
              <button className="primary" disabled={busy} onClick={() => run(() => api.signoff(meta.id))}>签核通过</button>
              <button className="ghost" disabled={busy} onClick={() => setReasoning(true)}>退回</button>
            </div>
          )}
          {meta.type === 'layout' && meta.status === 'pending_template' && (
            <>
              <p className="muted">{workflow?.reason ?? '已签核。在 agent 里说“处理待办”继续模板制作。'}</p>
              <div className="panel-row">
                <button disabled={busy} onClick={() => setReasoning(true)}>撤回签核</button>
              </div>
            </>
          )}
          {meta.type === 'template' && meta.status === 'draft' && <p className="muted">{workflow?.reason ?? '模板待完成回放与作者确认。'}</p>}
          {meta.type === 'method' && meta.status === 'draft' && (
            <>
              <p className="muted">方法笔记已写好。读完用途、适用与代码后再确认。</p>
              <div className="panel-row">
                <button className="primary" disabled={busy} onClick={() => run(() => api.confirm(meta.id))}>确认笔记</button>
                <button className="ghost" disabled={busy} onClick={() => setReasoning(true)}>退回</button>
              </div>
            </>
          )}
          {meta.type === 'method' && meta.status === 'ready' && (
            <div className="panel-row">
              <button className="ghost" disabled={busy} onClick={() => setReasoning(true)}>退回修改</button>
            </div>
          )}
        </>
      )}

      <div className="panel-row end">
        {meta.status === 'archived' ? (
          <button className="ghost" disabled={busy} onClick={() => run(() => api.restore(kind, meta.id))}>恢复</button>
        ) : (
          <button className="ghost danger" disabled={busy} onClick={() => run(() => api.archive(kind, meta.id))}>归档</button>
        )}
      </div>
      {onDeleted && <DeleteArchived meta={meta} onDeleted={onDeleted} />}
    </div>
  );
}

export function TagsEditor({ meta, run, busy }: ActionProps) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(meta.tags.join('、'));

  if (!editing) {
    return (
      <div className="panel">
        <div className="panel-row">
          <h3>标签</h3>
          <button className="ghost small" onClick={() => setEditing(true)}>编辑</button>
        </div>
        {meta.tags.length === 0 ? (
          <p className="muted small">还没有标签。标签只帮助搜索，不影响它能用在哪里。</p>
        ) : (
          <div className="chips">
            {meta.tags.map((tag) => (
              <span key={tag} className="chip">{tag}</span>
            ))}
          </div>
        )}
      </div>
    );
  }

  const save = () => {
    const tags = [...new Set(text.split(/[,，、\n]/).map((t) => t.trim()).filter(Boolean))];
    run(() => api.tags(KIND_OF[meta.type], meta.id, tags)).then((ok) => { if (ok) setEditing(false); });
  };

  return (
    <div className="panel stack">
      <label htmlFor="tags">标签（用顿号或逗号分隔，可留空）</label>
      <input id="tags" value={text} onChange={(e) => setText(e.target.value)} />
      <div className="panel-row">
        <button className="primary" disabled={busy} onClick={save}>保存</button>
        <button className="ghost" onClick={() => setEditing(false)}>取消</button>
      </div>
    </div>
  );
}
export function NoteEditor({ meta, note, run, busy }: ActionProps & { note: string }) {
  const [text, setText] = useState(note);
  const dirty = text !== note;
  return (
    <div className="panel stack">
      <label htmlFor="note"><h3>我的备注</h3></label>
      <p className="muted small">agent 推荐时会读到，但不会改写这里。</p>
      <textarea id="note" rows={5} value={text} onChange={(e) => setText(e.target.value)} />
      <button className="primary" disabled={busy || !dirty} onClick={() => run(() => api.note(KIND_OF[meta.type], meta.id, text))}>保存备注</button>
    </div>
  );
}

export function MethodSource({ meta }: { meta: MethodMeta }) {
  const { source } = meta;
  return (
    <div className="panel small">
      <h3>来源与许可</h3>
      <dl className="facts">
        <dt>来源</dt>
        <dd>
          {source.kind === 'post' && '公众号帖子附带代码'}
          {source.kind === 'project' && '作者课题脚本'}
          {source.kind === 'repo' && (safeUrl(source.url)
            ? <a href={safeUrl(source.url)!} target="_blank" rel="noreferrer">{source.url}</a> : source.url)}
          {source.kind === 'written' && 'agent 依据文献与官方文档编写'}
        </dd>
        <dt>许可证</dt>
        <dd className={meta.license === 'none' ? 'warn' : ''}>{meta.license === 'none' ? '无许可证，仅供个人研究参考' : meta.license}</dd>
      </dl>
      <h3 className="spaced">应引用</h3>
      <ol className="cites">
        {meta.cite.map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ol>
    </div>
  );
}
