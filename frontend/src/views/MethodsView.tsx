import { InterfaceMeta, MethodMeta, PageSummary, STATUS_LABEL, Status } from '../api';
import type { AppData } from '../App';
import { MethodCard, TypeMark } from '../components';
import { pageLink } from '../nav';
import { methodFigures } from '../figureModels';

const PIPELINE: Status[] = ['draft', 'ready'];

export function MethodsView({ data }: { data: AppData }) {
  const byPath = new Map(data.pages.map((p) => [p.path, p]));
  const methods = data.pages.filter((p): p is PageSummary<MethodMeta> => p.meta.type === 'method' && p.meta.status !== 'archived');
  const interfaces = data.pages.filter((p): p is PageSummary<InterfaceMeta> => p.meta.type === 'interface');
  const title = (path: string) => byPath.get(path)?.meta.title ?? path;

  return (
    <section className="methods">
      <header className="hero slim">
        <div className="hero-text">
          <h1>方法库</h1>
          <p className="lede">
            每个方法家族写清目的、适用前提、原始实现与未验证分支。agent 先读当前课题的计划、数据和结果，再找有依据的方法与图样；选定后在课题环境适配和运行。页面可用、代码存在与运行验证分别记录。
          </p>
          <dl className="census">
            {PIPELINE.map((s) => (
              <div key={s}>
                <dt>
                  <span className={`dot status-${s}`} aria-hidden="true" />
                  {STATUS_LABEL[s]}
                </dt>
                <dd>{methods.filter((m) => m.meta.status === s).length}</dd>
              </div>
            ))}
          </dl>
        </div>
      </header>

      {methods.length === 0 ? (
        <p className="notice">还没有收录方法。在 agent 里说“把这段分析代码收进方法库”，或复刻带分析代码的帖子后同意抽成方法。</p>
      ) : (
        <div className="grid">
          {methods.map((m, i) => (
            <MethodCard
              key={m.path}
              path={m.path}
              meta={m.meta}
              number={i + 1}
              outputs={data.flow.outputs(m.path).map((path) => ({ path, title: title(path) }))}
              figures={methodFigures(m.path, data.pages, data.graph, data.flow)}
            />
          ))}
        </div>
      )}

      <div className="queue-section">
        <h2>
          <TypeMark type="interface" />
          数据接口
          <span className="count">{interfaces.length}</span>
        </h2>
        <p className="muted">方法与图之间的约定：一种标准表格。方法输出它，图模板读取它，文件名就是接口名。</p>
        <div className="interface-list">
          {interfaces.map((p) => (
            <article key={p.path} className="interface-row sheet">
              <h3>
                <a {...pageLink(p.path)}>{p.meta.title}</a>
                <code>{p.meta.slug}.csv</code>
              </h3>
              <div className="chips">
                {Object.entries(p.meta.columns).map(([name, col]) => (
                  <span key={name} className="chip" title={col.description}>
                    {name} <span className="muted">{col.type}</span>
                  </span>
                ))}
              </div>
              <p className="flowline">
                <span>
                  {data.flow.inputs(p.path).map((m) => (
                    <a key={m} {...pageLink(m)}>{title(m)}</a>
                  ))}
                </span>
                <span className="arrow" aria-label="输出给" />
                <span>
                  {data.flow.outputs(p.path).map((t) => (
                    <a key={t} {...pageLink(t)}>{title(t)}</a>
                  ))}
                </span>
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
