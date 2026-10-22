import { MethodMeta, PageSummary, displayStatus, effectiveStatus, imageOf, wikiFile } from '../api';
import { StatusBadge, FigureImage } from '../components';
import { MethodFigure, methodDisplayFigures, templateSourceNote } from '../figureModels';
import { pageLink } from '../nav';
import { COMPATIBILITY_LABEL, verificationLabel } from '../relations';
import { methodPurpose } from '../markdown';

interface Props {
  meta: MethodMeta;
  body: string;
  figures: MethodFigure[];
  pages: PageSummary[];
  hiddenSources?: Set<string>;
}

/** One view per plot style; analysis input/output and render adaptation stay distinct. */
export function MethodOverview({ meta, body, figures, pages, hiddenSources }: Props) {
  const shown = methodDisplayFigures(figures);
  const interfaces = (slugs: string[]) => slugs.map((slug) => {
    const path = `interfaces/${slug}.md`;
    return <a key={path} {...pageLink(path)}>{pages.find((p) => p.path === path)?.meta.title ?? slug}</a>;
  });
  return <section className="method-overview">
    <p className="method-purpose">{methodPurpose(body)}</p>
    <div className="method-data-grid">
      <div><h2>分析需要什么</h2>{meta.inputs.length ? interfaces(meta.inputs) : <p className="small">见下方输入说明中的模型、特征与背景条件。</p>}</div>
      <div><h2>分析得到什么</h2>{meta.outputs.length ? interfaces(meta.outputs) : <p className="small">尚未声明标准输出表，见方法说明。</p>}</div>
    </div>
    <h2>可以怎样画</h2>
    <p className="muted small">同一图样只展示一次，优先提供函数模板；来源保留在图样或模板详情中。兼容关系与运行验证分别说明。</p>
    {shown.length === 0 ? <p className="muted">暂无有依据的关联图样；方法笔记仍可独立使用。</p> : <div className="method-figure-grid">
      {shown.map((f) => <article key={f.path} className="method-visual">
        <a className="method-figure-link" {...pageLink(f.path)}>
          <span className="plate"><FigureImage key={imageOf(f.meta)} meta={f.meta} /></span>
          <strong>{f.meta.title}</strong>
        </a>
        <div className="method-visual-badges"><StatusBadge status={effectiveStatus(f.meta)} label={displayStatus(f.meta)} />
          <span className={`compatibility compatibility-${f.semantic?.compatibility ?? 'candidate'}`}>{f.semantic ? COMPATIBILITY_LABEL[f.semantic.compatibility] : f.relation === 'reference' ? '参考图样' : '仅结构匹配'}</span></div>
        {f.semantic && <><p className="small">{f.semantic.reason}</p>{f.semantic.compatibility === 'adaptable' && <p className="small adaptation-note"><b>使用前需准备：</b>{f.semantic.adaptation}</p>}<p className="muted small">分析到绘图：{verificationLabel(f.semantic.verification)}</p></>}
        {f.meta.type === 'template' && <p className="muted small source-note">{templateSourceNote(f.meta, pages, hiddenSources)}</p>}
        {!!f.sourceLinks?.length && <p className="small source-note">来源：{f.sourceLinks.map((s, i) => <a key={s.path} {...pageLink(s.path)} title={s.title}>{i ? ' · ' : ''}图样 {i + 1}</a>)}</p>}
      </article>)}
    </div>}
    <p className="small"><a href={wikiFile(`methods/${meta.id}.md`)} target="_blank" rel="noreferrer">查看完整 Wiki 记录与来源元数据</a></p>
  </section>;
}
