import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  api,
  PaperDetail,
  PaperFigureDetail,
  PaperPanelCodeResponse,
  PaperPanelItem,
  PaperSummary,
  paperHref,
  ReceiptCounts,
  safeUrl,
  studioHref,
} from '../api';
import type { AppData } from '../App';
import { CodeTextView } from '../CodeViewer';
import { pageLink } from '../nav';

const EVIDENCE_BADGE: Record<string, { label: string; className: string }> = {
  local_recompute: { label: '本地重算', className: 'evidence-tier-badge tier-local-recompute' },
  original_table: { label: '实测/补表', className: 'evidence-tier-badge tier-original-table' },
  proxy: { label: '代理重算', className: 'evidence-tier-badge tier-proxy' },
  excluded_schematic: { label: '示意图已排除', className: 'evidence-tier-badge tier-excluded' },
  excluded_wet_lab: { label: '湿实验已排除', className: 'evidence-tier-badge tier-excluded' },
  excluded_imaging: { label: '显微影像已排除', className: 'evidence-tier-badge tier-excluded' },
};

export function evidenceBadgeMeta(tier: string): { label: string; className: string } {
  return EVIDENCE_BADGE[tier] ?? { label: tier || '未分级', className: 'evidence-tier-badge tier-excluded' };
}

export function formatReceiptSummaryText(
  counts: (Partial<ReceiptCounts> & { present?: boolean; count?: number }) | null | undefined,
): string | null {
  if (!counts) return null;
  if (typeof counts.hash_matched === 'number' && typeof counts.total === 'number' && counts.total > 0) {
    const base = `已核对代码哈希 ${counts.hash_matched}/${counts.total}（其中 ${counts.smoke_tested ?? 0} 个已冒烟实跑）`;
    const warnings: string[] = [];
    if ((counts.hash_mismatched ?? 0) > 0) warnings.push(`哈希不符 ${counts.hash_mismatched}`);
    if ((counts.script_missing ?? 0) > 0) warnings.push(`缺失脚本 ${counts.script_missing}`);
    return warnings.length > 0 ? `${base} · ${warnings.join(' · ')}` : base;
  }
  if (counts.present) {
    return `已记录 ${counts.count ?? 0} 条 Panel 收据（未含哈希核对）`;
  }
  return null;
}

export function panelReceiptLabel(receipt: Record<string, unknown> | null | undefined): string {
  if (!receipt) return '';
  const status = typeof receipt.status === 'string' ? receipt.status.trim() : '';
  let base: string;
  if (status === 'smoke_tested') base = '已冒烟实跑';
  else if (status === 'generated') base = '仅登记脚本（未冒烟实跑）';
  else if (status === 'pass' || status === 'ok') base = '已通过';
  else if (status) base = status;
  else base = '已登记收据（状态未知）';

  if (receipt.script_missing === true) return `${base} · 脚本缺失`;
  if (receipt.hash_matched === false) return `${base} · 哈希不符`;
  return base;
}

export function isManifestOnlyFigure(fig: PaperFigureDetail): boolean {
  if (typeof fig.manifest_only === 'boolean') return fig.manifest_only;
  return !fig.replica_url && fig.panels.length > 0 && fig.panels.every((p) => p.is_excluded);
}

export function buildPanelRunCommand(scriptPath: string, panelKey: string): string {
  const clean = scriptPath.trim();
  if (!clean) return '';
  const outName = (panelKey || 'panel').replace(/[^A-Za-z0-9_-]+/g, '_') + '.png';
  if (clean.toLowerCase().endsWith('.py')) {
    return `python ${clean} --paper-root <PAPER_ROOT> --out ${outName}`;
  }
  return `Rscript --vanilla ${clean} --paper-root <PAPER_ROOT> --out ${outName}`;
}

export function PaperListSection({ papers }: { papers: PaperSummary[] }) {
  return (
    <section className="papers-hub">
      <header className="gallery-top-bar">
        <div className="gallery-title-group">
          <span className="studio-eyebrow">PAPER REPLICATION · 1:1 SHOWCASE</span>
          <h1>论文复刻展示栏</h1>
          <p className="muted small">
            按原论文完整图组（Main + Supp）呈现 1:1 复刻大图与原图并排对照，下挂逐 Panel 独立 CLI 脚本、输入表契约与跨论文通用模板复用入口。
          </p>
        </div>
        <div className="gallery-top-actions">
          <a className="button" href="#/gallery">浏览通用绘图模板</a>
          <a className="button primary" href="#/methods">进入分析方法库</a>
        </div>
      </header>

      {papers.length === 0 ? (
        <p className="notice">暂无已归档的论文复刻工作流。运行 <code>rwiki paper publish</code> 并配置 <code>panel-manifest.yaml</code> 后即可在此检阅。</p>
      ) : (
        <div className="papers-card-grid">
          {papers.map((paper) => {
            const reproducedCount = paper.reproduced_figure_count ?? paper.figure_count;
            const manifestOnly = paper.manifest_only_figures ?? [];
            const receiptText = formatReceiptSummaryText(
              paper.receipt_counts ?? (paper.has_receipts ? { present: true, count: paper.stats.computed } : null),
            );
            return (
              <article key={paper.workflow_id} className="sheet paper-summary-card">
                <a className="paper-card-cover" href={paperHref(paper.workflow_id)}>
                  {paper.cover_url ? (
                    <img src={paper.cover_url} alt={`${paper.title} Fig. 1 封面`} loading="lazy" />
                  ) : (
                    <span className="preview-empty">暂无封面预览图</span>
                  )}
                  <span className="paper-cover-fig-count">
                    {manifestOnly.length > 0
                      ? `${reproducedCount} 张复刻整图 · ${manifestOnly.length} 张仅清单排除`
                      : `${reproducedCount} 张复刻整图`}
                  </span>
                </a>
                <div className="paper-card-body">
                  <div className="paper-card-meta-pills">
                    {paper.journal && <span className="journal-style-pill">{paper.journal}</span>}
                    {paper.year && <span className="badge">{paper.year}</span>}
                    {paper.doi && <code className="paper-doi-chip">DOI: {paper.doi}</code>}
                    {receiptText && <span className="panel-receipt-pill">{receiptText}</span>}
                  </div>
                  <h2>
                    <a href={paperHref(paper.workflow_id)}>{paper.title}</a>
                  </h2>
                  {paper.summary && <p className="small muted paper-card-summary">{paper.summary}</p>}
                  <div className="paper-card-stats">
                    <span className="paper-stat-pill">复刻整图 {reproducedCount}</span>
                    {manifestOnly.length > 0 && (
                      <span className="paper-stat-pill excluded">
                        仅清单排除 {manifestOnly.length}（{manifestOnly.map((f) => f.label).join('、')}）
                      </span>
                    )}
                    <span className="paper-stat-pill">总 Panel {paper.stats.panels}</span>
                    <span className="paper-stat-pill computed">计算复现 {paper.stats.computed}</span>
                    <span className="paper-stat-pill excluded">已排除 {paper.stats.excluded_total}</span>
                    <span className="paper-stat-pill templates">提炼模板 {paper.stats.templates}</span>
                  </div>
                  <div className="paper-card-actions">
                    <a className="button primary small" href={paperHref(paper.workflow_id)}>
                      检阅 1:1 整图与 Panel 脚本
                    </a>
                    <a className="button small" {...pageLink(paper.workflow_page)}>
                      直达工作流页
                    </a>
                    {paper.project_page && (
                      <a className="ghost-link small" {...pageLink(paper.project_page)}>
                        课题走线卡
                      </a>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

function PanelCodeDrawer({
  workflowId,
  panel,
  onClose,
}: {
  workflowId: string;
  panel: PaperPanelItem;
  onClose: () => void;
}) {
  const [codeData, setCodeData] = useState<PaperPanelCodeResponse | null>(null);
  const [loading, setLoading] = useState(Boolean(panel.script_path));
  const [error, setError] = useState('');
  const [copyState, setCopyState] = useState('');
  const [cmdCopyState, setCmdCopyState] = useState('');

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener('keydown', onKey, true);
    return () => document.removeEventListener('keydown', onKey, true);
  }, [onClose]);

  useEffect(() => {
    if (!panel.script_path) {
      setLoading(false);
      setCodeData(null);
      return;
    }
    const ctrl = new AbortController();
    setLoading(true);
    setError('');
    api.paperPanelCode(workflowId, panel.script_path, ctrl.signal).then(
      (res) => {
        if (!ctrl.signal.aborted) {
          setCodeData(res);
          setLoading(false);
        }
      },
      (err: Error) => {
        if (!ctrl.signal.aborted) {
          setError(err.message);
          setLoading(false);
        }
      },
    );
    return () => ctrl.abort();
  }, [workflowId, panel.script_path]);

  const badge = evidenceBadgeMeta(panel.evidence_tier);
  const runCmd = buildPanelRunCommand(panel.script_path, panel.panel_key || panel.panel);
  const scriptFileName = panel.script_path ? panel.script_path.split('/').pop() || 'panel_script.R' : 'panel_script.R';

  const copyText = async (text: string, setter: (msg: string) => void, okMsg: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setter(okMsg);
      setTimeout(() => setter(''), 2000);
    } catch {
      setter('复制失败，请手动选中');
    }
  };

  const downloadScript = () => {
    if (!codeData?.text) return;
    const blob = new Blob([codeData.text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = scriptFileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      className="inline-studio-backdrop"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <aside className="panel-code-drawer sheet" role="dialog" aria-modal="true" aria-label={`Panel ${panel.panel_key || panel.panel} 独立脚本`}>
        <header className="panel-drawer-head">
          <div>
            <div className="panel-drawer-badges">
              <span className="panel-key-pill">{panel.panel_key || panel.panel}</span>
              <span className={badge.className}>{badge.label}</span>
              {panel.receipt && (
                <span className="panel-receipt-pill">
                  收据：{panelReceiptLabel(panel.receipt)}
                </span>
              )}
            </div>
            <h2>{panel.figure} · Panel {panel.panel}</h2>
            {panel.description && <p className="small muted">{panel.description}</p>}
          </div>
          <button type="button" className="ghost small" onClick={onClose}>
            关闭
          </button>
        </header>

        <div className="panel-drawer-body">
          {panel.input_tables.length > 0 && (
            <section className="panel-drawer-section">
              <h3>所需输入表</h3>
              <div className="panel-table-chips">
                {panel.input_tables.map((t) => (
                  <code key={t} className="sniff-chip">{t}</code>
                ))}
              </div>
            </section>
          )}

          {runCmd && (
            <section className="panel-drawer-section">
              <div className="panel-drawer-section-head">
                <h3>独立运行命令</h3>
                <button
                  type="button"
                  className="button small"
                  onClick={() => void copyText(runCmd, setCmdCopyState, '已复制运行命令')}
                >
                  {cmdCopyState || '复制运行命令'}
                </button>
              </div>
              <pre className="panel-run-cmd"><code>{runCmd}</code></pre>
            </section>
          )}

          {panel.template && (
            <section className="panel-drawer-section cross-paper-jump-card">
              <div className="cross-paper-jump-head">
                <div>
                  <span className="cross-paper-badge">跨论文复用示例</span>
                  <h3>
                    <a {...pageLink(panel.template.path)} onClick={onClose}>{panel.template.title}</a>
                  </h3>
                  <p className="small muted">
                    <code>{panel.template.id}</code>
                    {panel.template.style_tier && ` · ${panel.template.style_tier === 'default' ? '主推默认' : '顶刊画风变体'}`}
                    {panel.template.journal_style && ` · ${panel.template.journal_style}`}
                  </p>
                </div>
                <div className="cross-paper-jump-actions">
                  <a className="button small" {...pageLink(panel.template.path)} onClick={onClose}>
                    查看通用模板
                  </a>
                  <a className="button primary small" href={studioHref(panel.template.id)} onClick={onClose}>
                    打开 Studio 换数据试跑
                  </a>
                </div>
              </div>
            </section>
          )}

          <section className="panel-drawer-section">
            <div className="panel-drawer-section-head">
              <h3>Panel 独立 CLI 源码 {panel.script_path && <code>{panel.script_path}</code>}</h3>
              <div className="panel-drawer-code-actions">
                <button
                  type="button"
                  className="button small"
                  disabled={!codeData?.text}
                  onClick={() => codeData?.text && void copyText(codeData.text, setCopyState, '已复制脚本')}
                >
                  {copyState || '复制代码'}
                </button>
                <button
                  type="button"
                  className="button small"
                  disabled={!codeData?.text}
                  onClick={downloadScript}
                >
                  下载脚本
                </button>
              </div>
            </div>
            {!panel.script_path ? (
              <p className="notice small">此 Panel 尚未配置独立 <code>script_path</code>（可参阅工作流整图脚本或关联通用模板）。</p>
            ) : loading ? (
              <p role="status" className="small muted">正在加载脚本源码…</p>
            ) : error ? (
              <p className="notice error small" role="alert">读取脚本失败：{error}</p>
            ) : codeData?.text == null ? (
              <p className="notice small">{codeData?.note || '该文件暂不支持纯文本预览。'}</p>
            ) : (
              <>
                <p className="small muted">
                  语言：{codeData.language} · {codeData.size.toLocaleString()} 字节 · SHA-256: <code>{codeData.sha256.slice(0, 16)}…</code>
                </p>
                <CodeTextView text={codeData.text} />
              </>
            )}
          </section>
        </div>
      </aside>
    </div>
  );
}

function FigureLightbox({
  figure,
  viewMode,
  onChangeMode,
  onClose,
}: {
  figure: PaperFigureDetail;
  viewMode: 'replica' | 'side_by_side';
  onChangeMode: (next: 'replica' | 'side_by_side') => void;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener('keydown', onKey, true);
    return () => document.removeEventListener('keydown', onKey, true);
  }, [onClose]);

  const activeUrl = viewMode === 'side_by_side' && figure.side_by_side_url ? figure.side_by_side_url : figure.replica_url;

  return (
    <div
      className="paper-lightbox-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label={`${figure.label} 高清检阅灯箱`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="paper-lightbox-sheet sheet">
        <header className="paper-lightbox-head">
          <div>
            <strong>{figure.label}</strong>
            {figure.caption && <span className="small muted"> — {figure.caption}</span>}
          </div>
          <div className="paper-lightbox-controls">
            <button
              type="button"
              className={viewMode === 'replica' ? 'button primary small' : 'button small'}
              disabled={!figure.replica_url}
              onClick={() => onChangeMode('replica')}
            >
              1:1 复刻大图
            </button>
            <button
              type="button"
              className={viewMode === 'side_by_side' ? 'button primary small' : 'button small'}
              disabled={!figure.side_by_side_url}
              onClick={() => onChangeMode('side_by_side')}
            >
              原图并排对照
            </button>
            <button type="button" className="ghost small" onClick={onClose}>
              关闭 (Esc)
            </button>
          </div>
        </header>
        <div className="paper-lightbox-stage">
          {activeUrl ? <img src={activeUrl} alt={figure.label} /> : <span className="preview-empty">暂无图片</span>}
        </div>
      </div>
    </div>
  );
}

export function PaperDetailSection({ detail }: { detail: PaperDetail }) {
  const [figScope, setFigScope] = useState<'all' | 'main' | 'supp'>('all');
  const [selectedSlug, setSelectedSlug] = useState<string>(detail.figures[0]?.slug ?? '');
  const [viewMode, setViewMode] = useState<'replica' | 'side_by_side'>('replica');
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [activePanel, setActivePanel] = useState<PaperPanelItem | null>(null);

  const visibleFigures = useMemo(() => {
    if (figScope === 'main') return detail.figures.filter((f) => !f.is_supplementary);
    if (figScope === 'supp') return detail.figures.filter((f) => f.is_supplementary);
    return detail.figures;
  }, [detail.figures, figScope]);

  const currentFigure =
    visibleFigures.find((f) => f.slug === selectedSlug) ?? visibleFigures[0] ?? detail.figures[0] ?? null;

  useEffect(() => {
    if (currentFigure && currentFigure.slug !== selectedSlug) {
      setSelectedSlug(currentFigure.slug);
    }
  }, [currentFigure, selectedSlug]);

  const activeImageUrl =
    viewMode === 'side_by_side' && currentFigure?.side_by_side_url
      ? currentFigure.side_by_side_url
      : currentFigure?.replica_url ?? null;

  const activePx =
    viewMode === 'side_by_side' && currentFigure?.side_by_side_px?.length === 2
      ? currentFigure.side_by_side_px
      : currentFigure?.replica_px ?? [];

  const mainCount = detail.figures.filter((f) => !f.is_supplementary).length;
  const suppCount = detail.figures.filter((f) => f.is_supplementary).length;
  const reproducedFigureCount =
    detail.reproduced_figure_count ?? detail.figures.filter((f) => !isManifestOnlyFigure(f)).length;
  const manifestOnlyFigureCount =
    detail.manifest_only_figure_count ?? detail.figures.filter((f) => isManifestOnlyFigure(f)).length;
  const receiptText = formatReceiptSummaryText(detail.receipts_summary);
  const currentIsManifestOnly = currentFigure ? isManifestOnlyFigure(currentFigure) : false;
  const repoHref = safeUrl(detail.upstream_repo);

  return (
    <section className="paper-detail-view">
      <p className="crumb">
        <a href="#/papers">论文复刻</a> / <code>{detail.workflow_id}</code>
      </p>

      <header className="sheet paper-detail-hero">
        <div className="paper-detail-title-row">
          <div>
            <div className="paper-card-meta-pills">
              {detail.journal && <span className="journal-style-pill">{detail.journal}</span>}
              {detail.year && <span className="badge">{detail.year}</span>}
              {detail.doi && <code className="paper-doi-chip">DOI: {detail.doi}</code>}
              {receiptText && (
                <span className="panel-receipt-pill">
                  {receiptText}
                </span>
              )}
            </div>
            <h1>{detail.title}</h1>
            {detail.summary && <p className="muted small">{detail.summary}</p>}
          </div>
          <div className="paper-detail-hero-actions">
            <a className="button small" {...pageLink(detail.workflow_page)}>工作流详情页</a>
            {detail.project_page && (
              <a className="button small" {...pageLink(detail.project_page)}>课题走线实录卡</a>
            )}
            {repoHref && (
              <a className="button small" href={repoHref} target="_blank" rel="noreferrer">
                作者开源仓库 ↗
              </a>
            )}
          </div>
        </div>

        <div className="paper-card-stats">
          <span className="paper-stat-pill">复刻整图 {reproducedFigureCount}</span>
          {manifestOnlyFigureCount > 0 && (
            <span className="paper-stat-pill excluded">仅清单排除图组 {manifestOnlyFigureCount}</span>
          )}
          <span className="paper-stat-pill">总 Panel {detail.stats.panels}</span>
          <span className="paper-stat-pill computed">本地重算 {detail.stats.local_recompute}</span>
          <span className="paper-stat-pill original">实测/补表 {detail.stats.original_table}</span>
          <span className="paper-stat-pill proxy">代理重算 {detail.stats.proxy}</span>
          <span className="paper-stat-pill excluded">
            已排除 {detail.stats.excluded_total}（湿实验 {detail.stats.excluded_wet_lab} · 示意图 {detail.stats.excluded_schematic} · 影像 {detail.stats.excluded_imaging}）
          </span>
          <span className="paper-stat-pill templates">提炼通用模板 {detail.stats.templates}</span>
        </div>
      </header>

      <div className="sheet paper-figure-toolbar">
        <div className="paper-scope-pills" role="group" aria-label="主图与附图筛选">
          <button
            type="button"
            className={figScope === 'all' ? 'chip-btn active' : 'chip-btn'}
            onClick={() => setFigScope('all')}
          >
            全部 ({detail.figures.length})
          </button>
          <button
            type="button"
            className={figScope === 'main' ? 'chip-btn active' : 'chip-btn'}
            onClick={() => setFigScope('main')}
          >
            主图 Main ({mainCount})
          </button>
          <button
            type="button"
            className={figScope === 'supp' ? 'chip-btn active' : 'chip-btn'}
            onClick={() => setFigScope('supp')}
          >
            附图 Supp ({suppCount})
          </button>
        </div>

        <div className="paper-figure-tabs" role="tablist" aria-label="Figure 切换标签">
          {visibleFigures.map((fig) => {
            const figManifestOnly = isManifestOnlyFigure(fig);
            return (
              <button
                key={fig.slug}
                type="button"
                role="tab"
                aria-selected={currentFigure?.slug === fig.slug}
                className={currentFigure?.slug === fig.slug ? 'paper-fig-tab active' : 'paper-fig-tab'}
                onClick={() => setSelectedSlug(fig.slug)}
              >
                <span>{fig.label}</span>
                {figManifestOnly && <span className="paper-fig-manifest-tag">仅清单排除</span>}
                <span className="pill-count">{fig.panels.length || fig.declared_panels.length}</span>
              </button>
            );
          })}
        </div>
      </div>

      {currentFigure && (
        <div className="paper-workbench-grid">
          <section className="sheet paper-figure-inspector" aria-label="1:1 完整 Figure 检阅区">
            <div className="paper-inspector-head">
              <div>
                <h2>
                  {currentFigure.label}
                  {currentIsManifestOnly && (
                    <> <span className="evidence-tier-badge tier-excluded">仅清单排除（无复刻整图）</span></>
                  )}
                </h2>
                {currentFigure.caption && <p className="small muted">{currentFigure.caption}</p>}
              </div>
              <div className="paper-inspector-controls">
                <button
                  type="button"
                  className={viewMode === 'replica' ? 'button primary small' : 'button small'}
                  disabled={!currentFigure.replica_url}
                  onClick={() => setViewMode('replica')}
                >
                  1:1 复刻大图
                </button>
                <button
                  type="button"
                  className={viewMode === 'side_by_side' ? 'button primary small' : 'button small'}
                  disabled={!currentFigure.side_by_side_url}
                  onClick={() => setViewMode('side_by_side')}
                >
                  原图并排对照
                </button>
                <button
                  type="button"
                  className="button small"
                  disabled={!activeImageUrl}
                  onClick={() => setLightboxOpen(true)}
                >
                  放大检阅
                </button>
              </div>
            </div>

            <div className="paper-inspector-meta small muted">
              {activePx.length === 2 && <span>尺寸：{activePx[0]} × {activePx[1]} px</span>}
              {currentFigure.visual_review && <span>视觉门禁：{currentFigure.visual_review}</span>}
            </div>

            <div className="paper-figure-stage">
              {activeImageUrl ? (
                <button
                  type="button"
                  className="paper-figure-zoom-trigger"
                  onClick={() => setLightboxOpen(true)}
                  title="点击放大检阅细节"
                >
                  <img
                    key={activeImageUrl}
                    src={activeImageUrl}
                    alt={`${currentFigure.label} (${viewMode})`}
                    loading="lazy"
                  />
                </button>
              ) : currentIsManifestOnly ? (
                <p className="preview-empty">该图组仅在 Panel 清单中登记排除条目（全部 Panel 均属非计算排除分层），不生成 1:1 代码复刻整图。</p>
              ) : (
                <p className="preview-empty">此 Figure 暂未配置画廊预览图像。</p>
              )}
            </div>
          </section>

          <section className="sheet paper-panels-rail" aria-label="原子 Panel 面板栏">
            <div className="paper-panels-rail-head">
              <h2>原子 Panel 拆解 ({currentFigure.panels.length})</h2>
              <p className="small muted">点击任意计算 Panel 打开独立 CLI 脚本抽屉与模板复用卡。</p>
            </div>

            {currentFigure.panels.length === 0 ? (
              <p className="notice small">此 Figure 尚无已登记的原子 Panel 清单。</p>
            ) : (
              <div className="paper-atomic-panel-list">
                {currentFigure.panels.map((pan) => {
                  const badge = evidenceBadgeMeta(pan.evidence_tier);
                  const canInspectCode = !pan.is_excluded || Boolean(pan.script_path) || Boolean(pan.template);
                  return (
                    <article
                      key={pan.panel_key || pan.panel}
                      className={`paper-atomic-panel-card${pan.is_excluded ? ' excluded' : ''}`}
                    >
                      <div className="paper-atomic-panel-top">
                        <div className="paper-atomic-panel-id">
                          <span className="panel-key-pill">{pan.panel_letter || pan.panel}</span>
                          {pan.panel_key && <code className="small muted">{pan.panel_key}</code>}
                        </div>
                        <span className={badge.className}>{badge.label}</span>
                      </div>

                      {pan.description && <p className="small">{pan.description}</p>}

                      {pan.input_tables.length > 0 && (
                        <div className="paper-panel-tables small muted">
                          输入表：{pan.input_tables.map((t) => <code key={t}>{t}</code>)}
                        </div>
                      )}

                      <div className="paper-atomic-panel-foot">
                        {canInspectCode && !pan.is_excluded ? (
                          <button
                            type="button"
                            className="button primary small"
                            onClick={() => setActivePanel(pan)}
                          >
                            {pan.script_path ? '查看独立代码' : '查看 Panel 详情'}
                          </button>
                        ) : (
                          <span className="small muted">不纳入纯生信代码复刻</span>
                        )}
                        {pan.receipt && (
                          <span className="panel-receipt-pill">
                            {panelReceiptLabel(pan.receipt)}
                          </span>
                        )}
                      </div>

                      {pan.template && (
                        <div className="paper-panel-template-chip">
                          <span className="cross-paper-badge">跨论文复用示例</span>
                          <a {...pageLink(pan.template.path)}>{pan.template.title}</a>
                        </div>
                      )}
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      )}

      {activePanel &&
        typeof document !== 'undefined' &&
        createPortal(
          <PanelCodeDrawer
            workflowId={detail.workflow_id}
            panel={activePanel}
            onClose={() => setActivePanel(null)}
          />,
          document.body,
        )}

      {lightboxOpen &&
        currentFigure &&
        typeof document !== 'undefined' &&
        createPortal(
          <FigureLightbox
            figure={currentFigure}
            viewMode={viewMode}
            onChangeMode={setViewMode}
            onClose={() => setLightboxOpen(false)}
          />,
          document.body,
        )}
    </section>
  );
}

export function PapersView({ workflowId = '', data: _data }: { workflowId?: string; data: AppData }) {
  const [papers, setPapers] = useState<PaperSummary[] | null>(null);
  const [detail, setDetail] = useState<PaperDetail | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const ctrl = new AbortController();
    setError('');
    if (!workflowId) {
      setDetail(null);
      api.papers(ctrl.signal).then(
        (res) => {
          if (!ctrl.signal.aborted) setPapers(res.papers ?? []);
        },
        (err: Error) => {
          if (!ctrl.signal.aborted) setError(err.message);
        },
      );
    } else {
      setDetail(null);
      api.paper(workflowId, ctrl.signal).then(
        (res) => {
          if (!ctrl.signal.aborted) setDetail(res);
        },
        (err: Error) => {
          if (!ctrl.signal.aborted) setError(err.message);
        },
      );
    }
    return () => ctrl.abort();
  }, [workflowId]);

  if (error) {
    return (
      <p className="notice error" role="alert">
        加载论文复刻数据失败：{error}。<a href="#/papers">返回论文列表</a>
      </p>
    );
  }
  if (!workflowId) {
    if (!papers) return <p className="notice" role="status">正在加载已复刻论文列表…</p>;
    return <PaperListSection papers={papers} />;
  }
  if (!detail) return <p className="notice" role="status">正在加载论文 1:1 全图与 Panel 清单…</p>;
  return <PaperDetailSection detail={detail} />;
}
