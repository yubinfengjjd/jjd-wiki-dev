import { isItem, ItemMeta, PageSummary, Status } from '../api';
import { methodFigures } from '../figureModels';
import type { AppData } from '../App';
import { MethodCard, PlateCard } from '../components';
import { DeleteArchived } from '../DeleteArchived';
import { queueOf } from '../workflow';

const SECTIONS: { key: string; title: string; hint: string; dot: Status }[] = [
  {
    key: 'signoff',
    title: '待你签核',
    hint: '打开选定图样，把原图和复刻图对照着看一遍，再签核或退回。单 panel 可独立签核。',
    dot: 'pending_signoff',
  },
  {
    key: 'confirm',
    title: '待你确认',
    hint: '方法笔记或已完成回放的模板待你确认。模板请核对回放及数据来源，再在对话中确认，由 agent 标为可用。',
    dot: 'draft',
  },
  {
    key: 'agent',
    title: '等 agent 处理',
    hint: '只列仍需制作、补齐关联或完成回放的工作。已有模板继续处理；来源与模板不重复计数，等待你确认的内容列在上一栏。',
    dot: 'pending_template',
  },
  { key: 'archived', title: '已归档', hint: '不再被推荐。可打开详情恢复，或查看删除范围后永久删除 Wiki 条目；原始画廊保留。', dot: 'archived' },
];

export function QueueView({ data }: { data: AppData }) {
  const byPath = new Map(data.pages.map((p) => [p.path, p]));
  const items = data.pages.filter((p): p is PageSummary<ItemMeta> => isItem(p.meta));

  const card = ({ path, meta }: PageSummary<ItemMeta>, i: number) =>
    meta.type === 'method' ? (
      <MethodCard
        key={path}
        path={path}
        meta={meta}
        number={i + 1}
        outputs={data.flow.outputs(path).map((p) => ({ path: p, title: byPath.get(p)?.meta.title ?? p }))}
        figures={methodFigures(path, data.pages, data.graph, data.flow)}
      />
    ) : (
      <PlateCard key={path} path={path} meta={meta} number={i + 1} />
    );

  return (
    <section>
      <h1 className="page-title">待办与归档</h1>
      {SECTIONS.map(({ key, title, hint, dot }) => {
        const shown = items.filter((p) => key === 'archived' ? p.meta.status === 'archived' : queueOf(p) === key);
        return (
          <div key={key} className="queue-section">
            <h2>
              <span className={`dot status-${dot}`} aria-hidden="true" />
              {title}
              <span className="count">{shown.length}</span>
            </h2>
            <p className="muted">{hint}</p>
            {shown.length === 0 ? <p className="empty">这一栏是空的。</p> : <div className="grid">{shown.map((p, i) => key === 'archived' ? <div className="archived-entry" key={p.path}>{card(p, i)}<DeleteArchived meta={p.meta} onDeleted={data.reload} /></div> : card(p, i))}</div>}
          </div>
        );
      })}
    </section>
  );
}
