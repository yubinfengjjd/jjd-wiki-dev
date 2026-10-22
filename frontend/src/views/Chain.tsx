import { imageOf, PageSummary } from '../api';
import { TypeMark } from '../components';
import { pageLink } from '../nav';

interface Props {
  title: string;
  hint: string;
  /** Columns from analysis to figure; the page itself appears in one of them, marked `self`. */
  columns: { label: string; pages: PageSummary[]; empty?: string }[];
  self: string;
  /** Optional read-interface note, shown inside template cards. */
  detailOf?: (path: string) => string;
}

/** The analysis → figure chain around one page, drawn as columns joined by arrows. */
export function Chain({ title, hint, columns, self, detailOf }: Props) {
  return (
    <section className="chain-strip">
      <h2>{title}</h2>
      <p className="muted small">{hint}</p>
      <div className="chain-cols">
        {columns.map(({ label, pages, empty }, i) => (
          <div key={label} className="chain-step">
            {i > 0 && <span className="chain-arrow" aria-hidden="true" />}
            <div className="chain-stack">
              <span className="chain-label">{label}</span>
              {pages.length === 0 && <span className="muted small">{empty ?? '暂无'}</span>}
              {pages.map((p) => {
                const image = imageOf(p.meta);
                const detail = detailOf?.(p.path);
                const inner = (
                  <>
                    {image ? <img src={image} alt="" loading="lazy" /> : <TypeMark type={p.meta.type} />}
                    <span className="chain-copy">
                      <span>{p.meta.title}</span>
                      {detail && <span className="chain-detail small muted">{detail}</span>}
                    </span>
                  </>
                );
                return p.path === self ? (
                  <span key={p.path} className={`chain-item self ${image ? 'with-image' : ''}`}>{inner}</span>
                ) : (
                  <a key={p.path} className={`chain-item ${image ? 'with-image' : ''}`} {...pageLink(p.path)}>{inner}</a>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
