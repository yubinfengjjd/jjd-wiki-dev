import { PageSummary, ScenarioMeta } from '../api';
import type { AppData } from '../App';
import { TypeMark } from '../components';
import { pageLink } from '../nav';
import { resolvePick } from '../recipes';

/** Research scenarios: an entry point that lists the preferred recipes, templates and methods per question. */
export function ScenariosView({ data }: { data: AppData }) {
  const scenarios = data.pages.filter((p): p is PageSummary<ScenarioMeta> => p.meta.type === 'scenario');

  return (
    <section className="narrow scenarios">
      <h1 className="page-title">研究场景</h1>
      <p className="muted">
        每个场景列出某类研究问题的首选配方、模板与方法。打开场景页查看首选条目表、适用条件与注意事项；目录项只是上游列表，尚未在 Wiki 运行。
      </p>
      {scenarios.length === 0 ? (
        <p className="notice">还没有研究场景页。</p>
      ) : (
        <ul className="scenario-list">
          {scenarios.map((p) => {
            const picks = (Array.isArray(p.meta.picks) ? p.meta.picks : []).map((pick) => resolvePick(pick, data.pages));
            return (
              <li key={p.path} className="scenario-entry">
                <h2>
                  <TypeMark type="scenario" />
                  <a {...pageLink(p.path)}>{p.meta.title}</a>
                </h2>
                {p.meta.summary && <p>{p.meta.summary}</p>}
                {picks.length > 0 && (
                  <ol className="scenario-picks small" aria-label="首选条目">
                    {picks.map((pick, i) => (
                      <li key={`${pick.id}:${i}`}>
                        {pick.type && <TypeMark type={pick.type} />}
                        {pick.path ? <a {...pageLink(pick.path)}>{pick.title}</a> : pick.catalog ? <code>{pick.id}</code> : <span>{pick.id}</span>}
                        {pick.catalog && <span className="muted">（目录项，未在 Wiki 运行）</span>}
                        {!pick.path && !pick.catalog && <span className="muted">（页面不存在）</span>}
                        {pick.archived && <span className="muted">（已归档）</span>}
                        {pick.note && <span className="muted"> — {pick.note}</span>}
                      </li>
                    ))}
                  </ol>
                )}
                {!!p.meta.tags?.length && (
                  <div className="chips">
                    {p.meta.tags.map((tag) => (
                      <span key={tag} className="chip">{tag}</span>
                    ))}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
