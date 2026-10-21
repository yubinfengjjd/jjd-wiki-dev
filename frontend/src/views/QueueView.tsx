import { isItem, ItemMeta, PageSummary, Status, TemplateMeta } from '../api';
import type { AppData } from '../App';
import { MethodCard, PlateCard } from '../components';

/** Statuses that put an item on the to-do list (archived items have their own shelf). */
export const QUEUED = new Set<Status>(['pending_signoff', 'draft', 'pending_template']);

const SECTIONS: { key: string; title: string; hint: string; dot: Status; pick: (m: ItemMeta) => boolean }[] = [
  {
    key: 'signoff',
    title: '待你签核',
    hint: '打开整图，把原图和复刻图对照着看一遍，再签核或退回。',
    dot: 'pending_signoff',
    pick: (m) => m.status === 'pending_signoff',
  },
  {
    key: 'confirm',
    title: '待你确认',
    hint: '方法笔记已写好。打开读一遍用途、适用和代码，没问题就确认，有问题写明理由退回。',
    dot: 'draft',
    pick: (m) => m.type === 'method' && m.status === 'draft',
  },
  {
    key: 'agent',
    title: '等 agent 处理',
    hint: '在 Codex 或 Claude Code 里说“处理待办”：签核过的整图会被拆成单图模板并回放，草稿模板等待回放确认。',
    dot: 'pending_template',
    pick: (m) => m.status === 'pending_template' || (m.type !== 'method' && m.status === 'draft'),
  },
  { key: 'archived', title: '已归档', hint: '不再被推荐。打开详情可以恢复。', dot: 'archived', pick: (m) => m.status === 'archived' },
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
        figures={data.flow.figuresOf(path).map((p) => ({ path: p, meta: byPath.get(p)!.meta as TemplateMeta }))}
      />
    ) : (
      <PlateCard key={path} path={path} meta={meta} number={i + 1} />
    );

  return (
    <section>
      <h1 className="page-title">待办与归档</h1>
      {SECTIONS.map(({ key, title, hint, dot, pick }) => {
        const shown = items.filter((p) => pick(p.meta));
        return (
          <div key={key} className="queue-section">
            <h2>
              <span className={`dot status-${dot}`} aria-hidden="true" />
              {title}
              <span className="count">{shown.length}</span>
            </h2>
            <p className="muted">{hint}</p>
            {shown.length === 0 ? <p className="empty">这一栏是空的。</p> : <div className="grid">{shown.map(card)}</div>}
          </div>
        );
      })}
    </section>
  );
}
