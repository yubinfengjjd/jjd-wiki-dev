import { useState } from 'react';
import { api, galleryFile, ItemMeta, KIND_OF, LayoutMeta, MethodMeta, PageDetail, wikiFile } from '../api';
import { StatusBadge } from '../components';

type Run = (action: () => Promise<PageDetail>) => Promise<void>;

interface ActionProps {
  meta: ItemMeta;
  run: Run;
  busy: boolean;
}

/** Layout viewer: the replay of the whole figure first once it exists, then the gallery's own images. */
export function LayoutImages({ page, meta }: { page: PageDetail; meta: LayoutMeta }) {
  const files = page.gallery?.files ?? {};
  const views: [string, string][] = [];
  if (meta.status === 'ready') views.push(['按版式回放', wikiFile(`layouts/${meta.id}/preview.png`)]);
  if (files.compare) views.push(['并排对比', galleryFile(meta.gallery_entry, files.compare)]);
  if (files.output_png) views.push(['复刻图', galleryFile(meta.gallery_entry, files.output_png)]);
  if (files.source_image) views.push(['原图', galleryFile(meta.gallery_entry, files.source_image)]);
  const [active, setActive] = useState(0);

  if (views.length === 0) return null;
  return (
    <figure className="viewer">
      <div className="tabs" role="tablist">
        {views.map(([label], i) => (
          <button key={label} role="tab" aria-selected={i === active} className={i === active ? 'active' : ''} onClick={() => setActive(i)}>
            {label}
          </button>
        ))}
      </div>
      <a className="plate" style={{ viewTransitionName: 'plate' }} href={views[active][1]} target="_blank" rel="noreferrer">
        <img src={views[active][1]} alt={views[active][0]} />
      </a>
    </figure>
  );
}

export function SingleImage({ src, alt }: { src: string; alt: string }) {
  return (
    <figure className="viewer">
      <a className="plate" style={{ viewTransitionName: 'plate' }} href={src} target="_blank" rel="noreferrer">
        <img src={src} alt={alt} />
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

export function ItemActions({ meta, run, busy }: ActionProps) {
  const [reasoning, setReasoning] = useState(false);
  const kind = KIND_OF[meta.type];
  const withReason = (send: (reason: string) => Promise<PageDetail>) => (reason: string) => run(() => send(reason)).then(() => setReasoning(false));

  return (
    <div className="panel">
      <div className="panel-row">
        <StatusBadge status={meta.status} />
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
              <p className="muted">已签核。在 agent 里说“处理待办”即可拆成单图模板。</p>
              <div className="panel-row">
                <button disabled={busy} onClick={() => setReasoning(true)}>撤回签核</button>
              </div>
            </>
          )}
          {meta.type === 'template' && meta.status === 'draft' && <p className="muted">已拆出，等 agent 回放、你确认后可用。</p>}
          {meta.type === 'method' && meta.status === 'draft' && (
            <>
              <p className="muted">方法笔记已写好。读完用途、适用与代码后再确认。</p>
              <div className="panel-row">
                <button className="primary" disabled={busy} onClick={() => run(() => api.confirm(meta.id))}>确认可用</button>
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
    run(() => api.tags(KIND_OF[meta.type], meta.id, tags)).then(() => setEditing(false));
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
          {source.kind === 'repo' && <a href={source.url} target="_blank" rel="noreferrer">{source.url}</a>}
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
/** The reusable code templates under a method's code/ directory: what the agent copies into a project and adapts. */
export function CodeFiles({ meta, files }: { meta: MethodMeta; files: string[] }) {
  return (
    <section className="code-files">
      <h2>代码模板</h2>
      <p className="muted small">要改的参数集中在脚本开头；复制到课题目录改完再运行，知识库不运行它们。</p>
      <ul className="links">
        {files.map((name) => (
          <li key={name}>
            <code>{name}</code>
            <a href={wikiFile(`methods/${meta.id}/code/${name}`)} target="_blank" rel="noreferrer">查看</a>
          </li>
        ))}
      </ul>
    </section>
  );
}
