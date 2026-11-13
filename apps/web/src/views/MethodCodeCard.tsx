import { MethodMeta, PageSummary } from '../api';
import { CodeButton } from '../CodeViewer';
import { pageLink } from '../nav';
import { methodKindLabel, verifiedImplementations } from '../methods';

/** A discovery card preserves type, note status and per-branch evidence independently. */
export function MethodCodeCard({ page, pages }: { page: PageSummary<MethodMeta>; pages: PageSummary[] }) {
  const { meta } = page;
  const count = meta.implementations?.length ?? 0;
  const verified = verifiedImplementations(meta, page.implementation_status).length;
  const checked = (page.implementation_status?.length ?? 0) === count;
  const theories = (meta.theory_methods ?? []).flatMap(id => pages.filter(p =>
    p.meta.type === 'method' && p.meta.method_kind === 'analysis' && p.meta.id === id && p.meta.status !== 'archived'));
  return <article className="source-card method-code-card">
    <p className="muted small">{methodKindLabel(meta)} · {meta.status === 'ready' ? '笔记已确认' : '笔记待确认'}</p>
    <h3><a {...pageLink(page.path)}>{meta.title}</a></h3>
    {meta.summary && <p className="small">{meta.summary}</p>}
    {count > 0 && <p className="small">{checked ? `已验证 ${verified}/${count} 个实现；其余状态见详情` : '正在核对实现证据'}</p>}
    {!!meta.implementations?.length && <ul className="small code-entry-names">
      {meta.implementations.slice(0, 4).map(i => <li key={i.id}>{i.title}</li>)}
      {count > 4 && <li>另有 {count - 4} 个实现，见详情</li>}
    </ul>}
    {theories.length > 0 && <p className="small theory-links">方法理论：{theories.map(p => <a key={p.path} {...pageLink(p.path)}>{p.meta.title}</a>)}</p>}
    <div className="method-code-actions"><a {...pageLink(page.path)}>查看说明与验证范围</a>{count > 0 && <CodeButton meta={meta} />}</div>
  </article>;
}
