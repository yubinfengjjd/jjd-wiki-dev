import { useDeferredValue, useEffect, useMemo, useState } from 'react';
import { LANGUAGE, PlateCard } from '../components';
import { LayoutMeta, stageStatus, TemplateMeta, workflowOf } from '../api';
import type { AppData } from '../App';
import { DeleteTemplateModal } from '../DeleteTemplateModal';
import { FigureShelf, galleryEntries, galleryInventory, groupByOutputSlot, matchesFigureQuery, stylePillLabel, templateSourceNote } from '../figureModels';
import { matchesMethodQuery, plottingCodePages } from '../methods';
import { MethodCodeCard } from './MethodCodeCard';

interface Filters {
  q: string;
  tag: string;
  chart: string;
  language: string;
  status: string;
  favorite: boolean;
}

type Shelf = FigureShelf | 'code';
type FigureMeta = LayoutMeta | TemplateMeta;
type ViewMode = 'slot' | 'flat';

const EMPTY: Filters = { q: '', tag: '', chart: '', language: '', status: '', favorite: false };
const FLAT_PAGE_SIZE = 24;
const SHELVES: [Shelf, string][] = [
  ['single', '全部图样'],
  ['template', '可调用模版'],
  ['code', '绘图代码'],
];
const STAGES: Record<FigureShelf, [string, string][]> = {
  single: [
    ['complete', '模版已就绪'],
    ['template_confirm', '待确认'],
    ['template_work', '制作中'],
    ['signoff', '待签核'],
  ],
  template: [
    ['complete', '可用'],
    ['template_confirm', '待你确认'],
    ['template_work', '待完成回放'],
  ],
};

const progressOf = (meta: FigureMeta) => workflowOf(meta)?.stage ?? (meta.status === 'ready' ? 'complete' : meta.status);

function matches(meta: FigureMeta, f: Filters, query: string, pages: AppData['pages']): boolean {
  if (f.tag && !(meta.tags ?? []).includes(f.tag)) return false;
  if (f.chart && !(meta.chart_types ?? []).includes(f.chart)) return false;
  if (f.language && meta.language !== f.language) return false;
  if (f.status && progressOf(meta) !== f.status) return false;
  if (f.favorite && !meta.favorite) return false;
  if (!query) return true;
  return matchesFigureQuery(meta, query, pages);
}

const uniq = (values: string[]) => [...new Set(values)].sort();

export function Gallery({ data }: { data: AppData }) {
  const [f, setF] = useState<Filters>(EMPTY);
  const [shelf, setShelf] = useState<Shelf>('single');
  const [viewMode, setViewMode] = useState<ViewMode>('slot');
  const [flatLimit, setFlatLimit] = useState(FLAT_PAGE_SIZE);
  const [selectedBySlot, setSelectedBySlot] = useState<Record<string, string>>({});
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string; path: string } | null>(null);
  const [deleteNotice, setDeleteNotice] = useState('');

  const deferredQuery = useDeferredValue(f.q);

  const inventory = useMemo(
    () => galleryInventory(data.pages, data.env.hiddenSources),
    [data.pages, data.env.hiddenSources],
  );
  const entries = useMemo(() => galleryEntries(data.pages), [data.pages]);
  const codePages = useMemo(() => plottingCodePages(data.pages), [data.pages]);
  const templates = shelf === 'code' ? [] : entries[shelf];
  const stages = shelf === 'code' ? [] : STAGES[shelf];

  const shown = useMemo(
    () => templates.filter((t) => matches(t.meta, f, deferredQuery, data.pages)),
    [templates, f, deferredQuery, data.pages],
  );

  const slotGroups = useMemo(() => groupByOutputSlot(shown), [shown]);

  useEffect(() => {
    setFlatLimit(FLAT_PAGE_SIZE);
  }, [shelf, viewMode, f.tag, f.chart, f.language, f.status, f.favorite, deferredQuery]);

  const pickShelf = (next: Shelf) => {
    setShelf(next);
    setF({ ...EMPTY, q: f.q });
  };
  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => setF({ ...f, [key]: value });
  const hasFilters = Boolean(f.q || f.tag || f.chart || f.language || f.status || f.favorite);

  const tagsList = useMemo(() => uniq(templates.flatMap((t) => t.meta.tags ?? [])), [templates]);
  const chartsList = useMemo(() => uniq(templates.flatMap((t) => t.meta.chart_types ?? [])), [templates]);
  const langsList = useMemo(() => uniq(templates.map((t) => t.meta.language)), [templates]);

  const flatShown = viewMode === 'flat' ? shown.slice(0, flatLimit) : shown;
  const remainingFlat = Math.max(0, shown.length - flatShown.length);

  const requestDelete = (meta: TemplateMeta, path: string) => {
    setDeleteNotice('');
    setDeleteTarget({ id: meta.id, title: meta.title, path });
  };

  return (
    <section className="gallery hiplot-gallery">
      <header className="gallery-top-bar">
        <div className="gallery-title-group">
          <span className="studio-eyebrow">FIGURE-FIRST BIO-GALLERY</span>
          <h1>生物信息可视化图库</h1>
          <p className="muted small">
            已收录 <strong>{inventory.templates}</strong> 个可调参模版与 <strong>{inventory.styles}</strong> 种图样 · 选图即用，1 键打开工作台加载示例或上传自己的 CSV/TSV 出图
          </p>
        </div>
        <div className="gallery-top-actions">
          <a className="button" href="#/playbooks">按分析流程找图</a>
          <a className="button primary" href="#/studio">打开作图工作台</a>
        </div>
      </header>

      {deleteNotice && (
        <p className="notice success" role="status">
          {deleteNotice}{' '}
          <button type="button" className="ghost small" onClick={() => setDeleteNotice('')}>关闭</button>
        </p>
      )}

      <div className="gallery-explore-layout">
        {/* Left Clean Sidebar */}
        <aside className="gallery-sidebar sheet" aria-label="图库筛选侧栏">
          <div className="sidebar-block">
            <label className="sidebar-label" htmlFor="gallery-search-input">关键词搜索</label>
            <input
              id="gallery-search-input"
              type="search"
              placeholder="搜索标题、基因、图型、R/Python…"
              aria-label="搜索"
              value={f.q}
              onChange={(e) => set('q', e.target.value)}
            />
          </div>

          <div className="sidebar-block">
            <span className="sidebar-label">资源视图</span>
            <div className="sidebar-pills vertical" role="tablist" aria-label="图库分栏">
              {SHELVES.map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  aria-selected={shelf === key}
                  className={shelf === key ? 'sidebar-pill active' : 'sidebar-pill'}
                  onClick={() => pickShelf(key)}
                >
                  <span>{label}</span>
                  <span className="pill-count">{key === 'code' ? codePages.length : entries[key].length}</span>
                </button>
              ))}
            </div>
          </div>

          {shelf !== 'code' && (
            <>
              <div className="sidebar-block">
                <span className="sidebar-label">开发语言</span>
                <div className="sidebar-pills">
                  <button
                    type="button"
                    className={!f.language ? 'chip-btn active' : 'chip-btn'}
                    onClick={() => set('language', '')}
                  >
                    全部
                  </button>
                  {langsList.map((lang) => (
                    <button
                      key={lang}
                      type="button"
                      className={f.language === lang ? 'chip-btn active' : 'chip-btn'}
                      onClick={() => set('language', f.language === lang ? '' : lang)}
                    >
                      {LANGUAGE[lang] ?? lang}
                    </button>
                  ))}
                </div>
              </div>

              {tagsList.length > 0 && (
                <div className="sidebar-block">
                  <label className="sidebar-label" htmlFor="gallery-tag-select">分析领域 / 标签</label>
                  <select id="gallery-tag-select" aria-label="标签" value={f.tag} onChange={(e) => set('tag', e.target.value)}>
                    <option value="">全部领域 ({tagsList.length})</option>
                    {tagsList.map((tag) => (
                      <option key={tag} value={tag}>{tag}</option>
                    ))}
                  </select>
                </div>
              )}

              {chartsList.length > 0 && (
                <div className="sidebar-block">
                  <label className="sidebar-label" htmlFor="gallery-chart-select">图表类型</label>
                  <select id="gallery-chart-select" aria-label="图型" value={f.chart} onChange={(e) => set('chart', e.target.value)}>
                    <option value="">全部图型 ({chartsList.length})</option>
                    {chartsList.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              )}

              <div className="sidebar-block">
                <label className="sidebar-label" htmlFor="gallery-status-select">验证状态</label>
                <select id="gallery-status-select" aria-label="状态" value={f.status} onChange={(e) => set('status', e.target.value)}>
                  <option value="">全部状态</option>
                  {stages.map(([s, label]) => (
                    <option key={s} value={s}>
                      {label} ({templates.filter((t) => progressOf(t.meta) === s).length})
                    </option>
                  ))}
                </select>
              </div>

              <div className="sidebar-block sidebar-row-actions">
                <label className="check small">
                  <input type="checkbox" checked={f.favorite} onChange={(e) => set('favorite', e.target.checked)} />
                  只看收藏
                </label>
                {hasFilters && (
                  <button type="button" className="ghost small" onClick={() => setF(EMPTY)}>
                    清空筛选
                  </button>
                )}
              </div>
            </>
          )}
        </aside>

        {/* Right Clean Figure Grid */}
        <div className="gallery-main-stage">
          {shelf === 'code' ? (
            <>
              <div className="gallery-result-bar">
                <span className="small muted">共 {codePages.filter((p) => matchesMethodQuery(p.meta, deferredQuery)).length} 条绘图代码（原生/自定义函数）</span>
              </div>
              <PlottingCodeShelf data={data} query={deferredQuery} />
            </>
          ) : (
            <>
              <div className="gallery-result-bar">
                <div className="gallery-result-summary">
                  <span className="small muted">
                    {viewMode === 'slot' ? (
                      <>
                        共 <strong>{slotGroups.length}</strong> 个输出槽位（覆盖 {shown.length} / {templates.length} 个{shelf === 'template' ? '可调用模版' : '图样'}）
                      </>
                    ) : (
                      <>
                        当前显示 <strong>{flatShown.length}</strong> / {shown.length} 个{shelf === 'template' ? '可调用模版' : '图样'}
                      </>
                    )}
                  </span>
                  <div className="gallery-view-toggle" role="group" aria-label="图库视图切换">
                    <button
                      type="button"
                      className={viewMode === 'slot' ? 'chip-btn active' : 'chip-btn'}
                      aria-pressed={viewMode === 'slot'}
                      onClick={() => setViewMode('slot')}
                    >
                      按输出槽位分组
                    </button>
                    <button
                      type="button"
                      className={viewMode === 'flat' ? 'chip-btn active' : 'chip-btn'}
                      aria-pressed={viewMode === 'flat'}
                      onClick={() => setViewMode('flat')}
                    >
                      平铺全部
                    </button>
                  </div>
                </div>
                <div className="status-legend small muted">
                  {stages.slice(0, 3).map(([s, label]) => (
                    <span key={s} className="legend-dot-item">
                      <span className={`dot status-${stageStatus(s) ?? s}`} aria-hidden="true" />
                      {label}: {templates.filter((t) => progressOf(t.meta) === s).length}
                    </span>
                  ))}
                </div>
              </div>

              {shown.length === 0 ? (
                <p className="notice">
                  {templates.length > 0
                    ? '没有符合当前筛选条件的图样，点击左侧「清空筛选」试试。'
                    : '本栏尚无图样。'}
                </p>
              ) : viewMode === 'slot' ? (
                <div className="grid hiplot-grid">
                  {slotGroups.map((group, i) => {
                    const selectedPath = selectedBySlot[group.slotKey];
                    const active = group.items.find((it) => it.path === selectedPath) ?? group.defaultItem;
                    const siblingSubjects = group.items.map((it) => ({
                      id: it.meta.id,
                      title: it.meta.title,
                      style_tier: it.meta.type === 'template' ? it.meta.style_tier : undefined,
                      journal_style: it.meta.type === 'template' ? it.meta.journal_style : undefined,
                    }));
                    const switcher = group.items.length > 1 ? (
                      <div className="slot-style-switcher" role="group" aria-label={`切换 ${group.primaryChart} 期刊画风`}>
                        <span className="slot-switcher-label">画风 ({group.items.length})</span>
                        <div className="slot-switcher-pills">
                          {group.items.map((variant, idx) => {
                            const isSelected = variant.path === active.path;
                            return (
                              <button
                                key={variant.path}
                                type="button"
                                className={isSelected ? 'slot-pill active' : 'slot-pill'}
                                aria-pressed={isSelected}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedBySlot((prev) => ({ ...prev, [group.slotKey]: variant.path }));
                                }}
                                title={`${variant.meta.title} (${variant.meta.id})`}
                              >
                                {stylePillLabel(siblingSubjects[idx], siblingSubjects)}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    ) : undefined;
                    return (
                      <PlateCard
                        key={group.slotKey}
                        path={active.path}
                        meta={active.meta}
                        number={i + 1}
                        sourceLinks={active.sourceLinks}
                        asStyle={shelf === 'single'}
                        paperOrigins={active.paper_origins}
                        note={active.meta.type === 'template' ? templateSourceNote(active.meta, data.pages, data.env.hiddenSources) : undefined}
                        styleCount={group.items.length > 1 ? group.items.length : undefined}
                        slotSwitcher={switcher}
                        onRequestDelete={requestDelete}
                      />
                    );
                  })}
                </div>
              ) : (
                <>
                  <div className="grid hiplot-grid">
                    {flatShown.map((t, i) => (
                      <PlateCard
                        key={t.path}
                        path={t.path}
                        meta={t.meta}
                        number={i + 1}
                        sourceLinks={t.sourceLinks}
                        asStyle={shelf === 'single'}
                        paperOrigins={t.paper_origins}
                        note={t.meta.type === 'template' ? templateSourceNote(t.meta, data.pages, data.env.hiddenSources) : undefined}
                        onRequestDelete={requestDelete}
                      />
                    ))}
                  </div>
                  {remainingFlat > 0 && (
                    <div className="gallery-load-more">
                      <button
                        type="button"
                        className="button"
                        onClick={() => setFlatLimit((prev) => prev + FLAT_PAGE_SIZE)}
                      >
                        加载更多（剩余 {remainingFlat} 个）
                      </button>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      </div>

      {deleteTarget && (
        <DeleteTemplateModal
          templateId={deleteTarget.id}
          templateTitle={deleteTarget.title}
          templatePath={deleteTarget.path}
          onClose={() => setDeleteTarget(null)}
          onDeleted={(result) => {
            const target = deleteTarget;
            setDeleteTarget(null);
            data.removePageLocally?.(target.path);
            setDeleteNotice(`已安全删除模版「${target.title}」（审计记录：${result.audit}）。`);
          }}
        />
      )}
    </section>
  );
}

export function PlottingCodeShelf({ data, query = '' }: { data: AppData; query?: string }) {
  const pages = plottingCodePages(data.pages).filter((p) => matchesMethodQuery(p.meta, query));
  return pages.length ? (
    <div className="source-grid">{pages.map((page) => <MethodCodeCard key={page.path} page={page} pages={data.pages} />)}</div>
  ) : (
    <p className="notice">没有匹配的绘图代码。可清空关键词，或到方法库浏览。</p>
  );
}
