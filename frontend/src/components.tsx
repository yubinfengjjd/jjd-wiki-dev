import { PointerEvent, ReactNode, useRef, useState } from 'react';
import { imageOf, previewOf, workflowOf, displayStatus, effectiveStatus, ImplementationStatus, ItemMeta, LayoutMeta, MethodMeta, PageMeta, PageType, RecipeMeta, STATUS_LABEL, Status, TemplateMeta } from './api';
import { pageLink } from './nav';
import { figureLabel, MethodFigure, methodFigureStatusLabel, methodPlateFigures, SourceLink } from './figureModels';
import { CodeButton } from './CodeViewer';
import { COMPATIBILITY_LABEL } from './relations';
import { verifiedImplementations } from './methods';
import { isNonCommercial, licenseLabel } from './recipes';

export function StatusBadge({ status, label }: { status: Status; label?: string }) {
  return <span className={`badge status-${status}`}>{label ?? STATUS_LABEL[status]}</span>;
}

/** The legend mark for a page type: the same disc, square or diamond the graph draws. */
export function TypeMark({ type }: { type: PageType }) {
  return <span className={`mark type-${type}`} aria-hidden="true" />;
}

export const LANGUAGE: Record<string, string> = { python: 'Python', r: 'R' };

const HINT: Record<ItemMeta['type'], Partial<Record<Status, string>>> = {
  layout: {
    pending_signoff: '等你对照原图签核。',
    pending_template: '已签核，等 agent 拆成单图模板。',
    ready: '可以按已确认的来源范围套用。',
    archived: '已归档，不会被推荐。',
  },
  template: {
    draft: '已拆出，等回放确认。',
    ready: '可以单独换数据套用。',
    archived: '已归档，不会被推荐。',
  },
  method: {
    draft: '笔记待完成或待你确认。',
    ready: '笔记已确认，具体实现按各自验证记录判断。',
    archived: '已归档，不会被推荐。',
  },
  recipe: {
    draft: '已入库，原样运行通过后待你确认。',
    ready: '已确认，可原样运行；运行通过不等于科学有效。',
    archived: '已归档，不会被推荐。',
  },
};

export const hintOf = (meta: ItemMeta) => workflowOf(meta)?.reason ?? HINT[meta.type][meta.status] ?? STATUS_LABEL[meta.status];

/** The card leans towards the pointer like a plate picked up from the table. */
function tilt(e: PointerEvent<HTMLElement>) {
  const el = e.currentTarget;
  const r = el.getBoundingClientRect();
  const x = (e.clientX - r.left) / r.width;
  const y = (e.clientY - r.top) / r.height;
  el.style.setProperty('--rx', `${(0.5 - y) * 7}deg`);
  el.style.setProperty('--ry', `${(x - 0.5) * 9}deg`);
  el.style.setProperty('--gx', `${x * 100}%`);
  el.style.setProperty('--gy', `${y * 100}%`);
}

function untilt(e: PointerEvent<HTMLElement>) {
  for (const p of ['--rx', '--ry', '--gx', '--gy']) e.currentTarget.style.removeProperty(p);
}

interface CardShell {
  path: string;
  meta: ItemMeta;
  number: number;
  label: string;
  plate: ReactNode;
  back: ReactNode;
  note?: string;
  sourceLinks?: SourceLink[];
  execution?: string;
  /** Extra marks beside the status badge, e.g. a recipe's licence. */
  badges?: ReactNode;
}

/** Card stock with a figure plate on the front and a summary on the back. */
function Card({ path, meta, number, label, plate, back, note, sourceLinks, execution, badges }: CardShell) {
  const [flipped, setFlipped] = useState(false);
  const plateRef = useRef<HTMLDivElement>(null);
  const link = pageLink(path, () => plateRef.current);

  return (
    <article className={flipped ? 'plate-card flipped' : 'plate-card'} onPointerMove={tilt} onPointerLeave={untilt}>
      <div className="plate-turn">
        <a className="face front" {...link} aria-hidden={flipped} tabIndex={flipped ? -1 : 0}>
          <div className={`plate ${meta.type}`} ref={plateRef}>
            {plate}
            {meta.favorite && <span className="fav" aria-label="已收藏">★</span>}
          </div>
          <div className="caption">
            <h3>
              <span className="fig-no">{label} {number}</span>
              {meta.title}
            </h3>
            {note && <p className="caption-note muted small">{note}</p>}
            <div className="caption-foot">
              <StatusBadge status={effectiveStatus(meta)} label={displayStatus(meta)} />
              {badges}
              {execution && <span className="method-execution small">{execution}</span>}
              {'language' in meta && <span className="lang">{LANGUAGE[meta.language] ?? meta.language}</span>}
            </div>
          </div>
        </a>
        <div className="face back" aria-hidden={!flipped}>
          <p className="back-title">{label} {number} 背面</p>
          <dl>
            <dt>状态</dt>
            <dd>{hintOf(meta)}</dd>
            {back}
          </dl>
          <a className="button primary" {...link} tabIndex={flipped ? 0 : -1}>打开</a>
        </div>
      </div>
      {sourceLinks && sourceLinks.length > 1 && <nav className="card-sources small" aria-label="此图样的来源">{sourceLinks.map((s, i) => <a key={s.path} {...pageLink(s.path)} title={s.title}>来源 {i + 1}</a>)}</nav>}
      <CodeButton meta={meta} className="card-code" />
      <button className="turn" onClick={() => setFlipped(!flipped)} aria-pressed={flipped} aria-label={flipped ? '翻回正面' : '翻到背面'}>
        <svg viewBox="0 0 20 20" aria-hidden="true">
          <path d="M4 7a6 6 0 0 1 11-1.5M16 13a6 6 0 0 1-11 1.5M15 2.5v3.5h-3.5M5 17.5V14h3.5" />
        </svg>
      </button>
    </article>
  );
}

interface FigureProps {
  path: string;
  meta: LayoutMeta | TemplateMeta;
  number: number;
  note?: string;
  asStyle?: boolean;
  sourceLinks?: SourceLink[];
}

export function FigureImage({ meta }: { meta: PageMeta }) {
  const src = imageOf(meta);
  const [failed, setFailed] = useState(false);
  const preview = previewOf(meta);
  // A recipe's picture is only ever its latest passing as-is run; there is no stand-in.
  if (!src || failed) return <span className="preview-empty">{meta.type === 'recipe' ? '暂无运行图' : '暂无预览图'}</span>;
  return <>
    <img key={src} src={src} alt={preview?.label ?? '图样预览'} loading="lazy" onError={() => setFailed(true)} />
    {(preview?.kind === 'pending' || (meta.type === 'template' && (preview?.kind === 'source' || preview?.kind === 'stale'))) && <span className="preview-label">{preview.label}</span>}
  </>;
}

export function PlateCard({ path, meta, number, note, asStyle = false, sourceLinks }: FigureProps) {
  return (
    <Card
      path={path}
      meta={meta}
      number={number}
      label={asStyle ? '单 panel 图样' : figureLabel(meta)}
      note={note}
      sourceLinks={sourceLinks}
      plate={<FigureImage key={imageOf(meta)} meta={meta} />}
      back={
        <>
          <dt>图型</dt>
          <dd>{meta.chart_types.join('、')}</dd>
          {meta.type === 'layout' && (
            <>
              <dt>面板</dt>
              <dd>{Object.keys(meta.panels).length} 个逻辑 panel；{meta.templates.length ? `已有 ${meta.templates.length} 个可调用模板` : '可调用模板尚待制作'}</dd>
            </>
          )}
          {/* v2 templates derived from a recipe have no source panels; their origin is the front note. */}
          {meta.type === 'template' && !!meta.panels?.length && (
            <>
              <dt>出自</dt>
              <dd>原图面板 {meta.panels.join('、')}</dd>
            </>
          )}
          {meta.tags.length > 0 && (
            <>
              <dt>标签</dt>
              <dd>{meta.tags.join('、')}</dd>
            </>
          )}
        </>
      }
    />
  );
}

/** Non-commercial licences read as "非商业" at a glance; the SPDX id stays in the tooltip. */
export function LicenseBadge({ license }: { license: string | null | undefined }) {
  return (
    <span className={isNonCommercial(license) ? 'license-badge nc' : 'license-badge'} title={license ? `许可证：${license}` : '许可证未记录'}>
      {licenseLabel(license)}
    </span>
  );
}

interface RecipeProps {
  path: string;
  meta: RecipeMeta;
  number: number;
  /** Source library and upstream item, e.g. "FigureYa · FigureYa59volcanoV2". */
  origin: string;
}

/** A recipe's plate is its latest passing as-is run; the licence travels with it on the front. */
export function RecipeCard({ path, meta, number, origin }: RecipeProps) {
  const commit = meta.source?.commit ? String(meta.source.commit).slice(0, 12) : '';
  return (
    <Card
      path={path}
      meta={meta}
      number={number}
      label="配方"
      note={origin ? `来源：${origin}` : undefined}
      badges={<LicenseBadge license={meta.license} />}
      plate={<FigureImage key={imageOf(meta)} meta={meta} />}
      back={
        <>
          <dt>来源</dt>
          <dd>{origin || '未记录'}{commit && ` · commit ${commit}`}</dd>
          <dt>许可证</dt>
          <dd>{meta.license || '未记录'}{isNonCommercial(meta.license) && '（仅限非商业使用）'}</dd>
          {!!meta.chart_types?.length && (
            <>
              <dt>图型</dt>
              <dd>{meta.chart_types.join('、')}</dd>
            </>
          )}
          {!!meta.tags?.length && (
            <>
              <dt>标签</dt>
              <dd>{meta.tags.join('、')}</dd>
            </>
          )}
        </>
      }
    />
  );
}

interface MethodProps {
  path: string;
  meta: MethodMeta;
  number: number;
  outputs: { path: string; title: string }[];
  figures: MethodFigure[];
  implementationStatus?: ImplementationStatus[];
}

/** A method's plate is its chain: the tables it writes, flowing into the figures they can draw. */
export function MethodCard({ path, meta, number, outputs, figures, implementationStatus }: MethodProps) {
  const verified = verifiedImplementations(meta, implementationStatus).length;
  return (
    <Card
      path={path}
      meta={meta}
      number={number}
      label="分析家族"
      note={meta.summary}
      execution={verified ? `已验证 ${verified}/${meta.implementations?.length ?? 0} 个实现` : '暂无已验证实现'}
      plate={<ChainPlate outputs={outputs} figures={figures} />}
      back={
        <>
          <dt>输出</dt>
          <dd>{outputs.map((o) => o.title).join('、')}</dd>
          <dt>语义关联图样</dt>
          <dd>{figures.filter((f) => f.relation === 'semantic').map((f) => `${f.meta.title}（${COMPATIBILITY_LABEL[f.semantic!.compatibility]}）`).join('、') || '暂无'}</dd>
          <dt>接口结构匹配</dt>
          <dd>{figures.filter((f) => f.relation === 'compatible').map((f) => f.meta.title).join('、') || '暂无'}</dd>
          <dt>相关参考图样</dt>
          <dd>{figures.filter((f) => f.relation === 'reference').map((f) => f.meta.title).join('、') || '暂无'}</dd>
          <dt>引用</dt>
          <dd>{meta.cite.length} 篇</dd>
          <dt>许可证</dt>
          <dd>{meta.license === 'none' ? '无，仅供个人研究参考' : meta.license}</dd>
        </>
      }
    />
  );
}

function ChainPlate({ outputs, figures }: Pick<MethodProps, 'outputs' | 'figures'>) {
  const shown = methodPlateFigures(figures);
  const pictured = shown.flatMap((f) => { const src = imageOf(f.meta); return src ? [{ f, src }] : []; });
  return (
    <div className="chain" aria-hidden="true">
      <span className="chain-fan">
        {pictured.map(({ f, src }, i) => (
          <img key={f.path} src={src} alt={f.meta.title} loading="lazy" style={{ ['--i' as string]: i - (pictured.length - 1) / 2 }} />
        ))}
      </span>
      {figures.length === 0 && <span className="chain-empty">尚无关联图样<br />文字方法笔记</span>}
      {shown.length > 0 && <span className="chain-ref-label">{shown[0].relation === 'semantic' ? COMPATIBILITY_LABEL[shown[0].semantic!.compatibility] : shown[0].relation === 'compatible' ? '接口结构匹配' : '参考图样'} · {methodFigureStatusLabel(shown[0])}</span>}
      <span className="chain-out">
        {outputs.length > 0 && <span className="chain-arrow" />}
        {outputs.map((o) => (
          <span key={o.path} className="chain-tag">
            <TypeMark type="interface" />
            {o.title}
          </span>
        ))}
      </span>
    </div>
  );
}
