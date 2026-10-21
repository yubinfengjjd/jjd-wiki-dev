import { PointerEvent, ReactNode, useRef, useState } from 'react';
import { imageOf, ItemMeta, LayoutMeta, MethodMeta, PageType, STATUS_LABEL, Status, TemplateMeta } from './api';
import { pageLink } from './nav';

export function StatusBadge({ status }: { status: Status }) {
  return <span className={`badge status-${status}`}>{STATUS_LABEL[status]}</span>;
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
    ready: '可以按原版式整张套用。',
    archived: '已归档，不会被推荐。',
  },
  template: {
    draft: '已拆出，等回放确认。',
    ready: '可以单独换数据套用。',
    archived: '已归档，不会被推荐。',
  },
  method: {
    draft: '笔记待完成或待你确认。',
    ready: '可以推荐。',
    archived: '已归档，不会被推荐。',
  },
};

export const hintOf = (meta: ItemMeta) => HINT[meta.type][meta.status] ?? STATUS_LABEL[meta.status];

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
}

/** Card stock with a figure plate on the front and a summary on the back. */
function Card({ path, meta, number, label, plate, back }: CardShell) {
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
            <div className="caption-foot">
              <StatusBadge status={meta.status} />
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
}

export function PlateCard({ path, meta, number }: FigureProps) {
  return (
    <Card
      path={path}
      meta={meta}
      number={number}
      label={meta.type === 'layout' ? '图' : '单图'}
      plate={<img src={imageOf(meta)!} alt="" loading="lazy" />}
      back={
        <>
          <dt>图型</dt>
          <dd>{meta.chart_types.join('、')}</dd>
          {meta.type === 'layout' && (
            <>
              <dt>面板</dt>
              <dd>{Object.keys(meta.panels).length} 个，拆成 {meta.templates.length} 个单图模板</dd>
            </>
          )}
          {meta.type === 'template' && (
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

interface MethodProps {
  path: string;
  meta: MethodMeta;
  number: number;
  outputs: { path: string; title: string }[];
  figures: { path: string; meta: TemplateMeta }[];
}

/** A method's plate is its chain: the tables it writes, flowing into the figures they can draw. */
export function MethodCard({ path, meta, number, outputs, figures }: MethodProps) {
  return (
    <Card
      path={path}
      meta={meta}
      number={number}
      label="方法"
      plate={<ChainPlate outputs={outputs} figures={figures} />}
      back={
        <>
          <dt>输出</dt>
          <dd>{outputs.map((o) => o.title).join('、')}</dd>
          <dt>可接的图</dt>
          <dd>{figures.map((f) => f.meta.title).join('、') || '暂无'}</dd>
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
  return (
    <div className="chain" aria-hidden="true">
      <span className="chain-fan">
        {figures.slice(0, 3).map((f, i) => (
          <img key={f.path} src={imageOf(f.meta)!} alt="" loading="lazy" style={{ ['--i' as string]: i - (Math.min(figures.length, 3) - 1) / 2 }} />
        ))}
      </span>
      <span className="chain-out">
        <span className="chain-arrow" />
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