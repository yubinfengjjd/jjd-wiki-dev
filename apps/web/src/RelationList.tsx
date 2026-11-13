import { displayStatus, effectiveStatus, type LayoutMeta, type PageSummary, type Relation, type TemplateMeta } from './api';
import { StatusBadge } from './components';
import { pageLink } from './nav';
import { relationLabel, relationTargetLabel, verificationLabel } from './relations';

/** A single view of the server's record, used unchanged from either end. */
export function RelationList({ relations, self, pages }: {
  relations: Relation[]; self: string; pages?: PageSummary[];
}) {
  return <section className="semantic-relations">
    <h2>方法与图的语义关系</h2>
    <p className="muted small">兼容状态说明知识上的对应关系；页面可用状态与实际运行验证分别记录。直接可接仍需检查当前课题的语义、单位与前提。</p>
    {relations.length === 0 ? <p className="muted">尚未记录语义关系。接口结构匹配与来源引用会另外展示，不能据此判断直接可接。</p> : <div className="relation-list">
      {relations.map((r) => {
        const methodSide = r.method === self;
        const target = pages?.find((page): page is PageSummary<LayoutMeta | TemplateMeta> =>
          page.path === r.figure
          && (page.meta.type === 'layout' || page.meta.type === 'template'));
        const figureStatus = target ? effectiveStatus(target.meta) : r.figure_status;
        const figureLabel = target ? displayStatus(target.meta) : undefined;
        const template = target?.meta.type === 'layout'
          ? (target.meta.templates ?? [])
            .map((id) => pages?.find((page) => page.path === `templates/${id}.md`))
            .find((page) => page?.meta.type === 'template' && page.meta.status === 'ready')
          : undefined;
        return <article key={`${r.method}:${r.figure}`} className={`relation-record${r.active ? '' : ' inactive'}`}>
          <div className="panel-row">
            <a {...pageLink(methodSide ? r.figure : r.method)}>{methodSide ? r.figure_title : r.method_title}</a>
            <span className={`compatibility compatibility-${r.compatibility}`}>{relationLabel(r)}</span>
          </div>
          <p className="small relation-target">{relationTargetLabel(r)}</p>
          <p>{r.reason}</p>
          <dl className="facts">
            <dt>方法页面</dt><dd><StatusBadge status={r.method_status} /></dd>
            <dt>图页面</dt><dd><StatusBadge status={figureStatus} label={figureLabel} /></dd>
            {template && <dt>可调用模板</dt>}
            {template && <dd><a {...pageLink(template.path)}>{template.meta.title}</a></dd>}
            <dt>前提</dt><dd>{r.prerequisites.length ? <ul>{r.prerequisites.map((p, i) => <li key={i}>{p}</li>)}</ul> : '未列出额外前提；使用前仍需核对'}</dd>
            <dt>适配动作</dt><dd>{r.adaptation || '未记录额外适配动作'}</dd>
            <dt>运行验证</dt><dd>{verificationLabel(r.verification)}</dd>
            <dt>验证范围</dt><dd>{r.verification?.scope || '范围未记录，不能据此承诺可运行'}</dd>
            <dt>关系依据</dt><dd>{r.evidence.length ? <ul>{r.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul> : '未提供'}</dd>
            {!!r.verification?.evidence?.length && <><dt>验证证据</dt><dd><ul>{r.verification.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul></dd></>}
          </dl>
          {!r.active && <p className="small muted">关联条目已归档或关系已停用，保留此记录用于追溯，不作为当前推荐。</p>}
        </article>;
      })}
    </div>}
  </section>;
}
