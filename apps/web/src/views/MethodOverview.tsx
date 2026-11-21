import { useState } from 'react';
import {
  AttachedVizBridged,
  AttachedVizCompatible,
  AttachedVizCurated,
  ImplementationStatus,
  InterfaceMeta,
  MethodHubDetail,
  MethodImplementation,
  MethodMeta,
  NextStepsResponse,
  PageSummary,
  paperHref,
  Status,
  studioHref,
  TemplateMeta,
  wikiFile,
  withThumbWidth,
} from '../api';
import { FigureImage, LicenseBadge, StatusBadge } from '../components';
import { MethodFigure, methodDisplayFigures, methodFigureStatusLabel, stylePillLabel, templateSourceNote } from '../figureModels';
import { pageLink } from '../nav';
import { COMPATIBILITY_LABEL, verificationLabel } from '../relations';
import {
  IMPLEMENTATION_LABEL,
  conditionFacts,
  domainLabel,
  domainsForMeta,
  entryKindLabel,
  methodKindLabel,
  packageFacts,
  portabilityLabel,
  runtimeModeLabel,
} from '../methods';

interface Props {
  meta: MethodMeta;
  purposeHtml?: string;
  implementationStatus?: ImplementationStatus[];
  figures: MethodFigure[];
  pages: PageSummary[];
  hiddenSources?: Set<string>;
  hub?: MethodHubDetail | null;
  nextSteps?: NextStepsResponse | null;
  onOpenStudio?: (templateId: string, templateTitle?: string) => void;
}

function TemplateActionBar({
  templateId,
  templateTitle,
  paperWorkflowId,
  onOpenStudio,
}: {
  templateId: string;
  templateTitle: string;
  paperWorkflowId?: string;
  onOpenStudio?: (id: string, title?: string) => void;
}) {
  const [copied, setCopied] = useState(false);
  const cliCommand = `rwiki render ${templateId} --data <数据目录> --bindings <bindings.json> --out <输出目录>`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(cliCommand);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="viz-card-actions">
      {onOpenStudio ? (
        <button
          type="button"
          className="button primary small"
          onClick={() => onOpenStudio(templateId, templateTitle)}
        >
          内联定制 / 试跑
        </button>
      ) : (
        <a className="button primary small" href={studioHref(templateId)}>
          打开工作台
        </a>
      )}
      <button type="button" className="button small" onClick={() => void handleCopy()} title={cliCommand}>
        {copied ? '已复制 CLI' : '复制 CLI 命令'}
      </button>
      <a className="button small" href={studioHref(templateId)}>
        派发到课题
      </a>
      {paperWorkflowId && (
        <a className="button small" href={paperHref(paperWorkflowId)}>
          查看论文 1:1 整图
        </a>
      )}
    </div>
  );
}

function StyleTierBadges({
  styleTier,
  journalStyle,
  tplPage,
}: {
  styleTier?: 'default' | 'variant';
  journalStyle?: string;
  tplPage?: PageSummary;
}) {
  const tplMeta = tplPage?.meta.type === 'template' ? (tplPage.meta as TemplateMeta) : undefined;
  const tier = styleTier ?? tplMeta?.style_tier ?? tplPage?.style_tier;
  const journal = journalStyle ?? tplMeta?.journal_style ?? tplPage?.journal_style;
  if (!tier && !journal) return null;
  return (
    <>
      {tier && (
        <span className={`style-tier-badge tier-${tier}`}>
          {tier === 'default' ? '主推默认' : '可切换画风'}
        </span>
      )}
      {journal && <span className="journal-style-pill">{journal}</span>}
    </>
  );
}

export interface PartitionedViz<T> {
  sorted: T[];
  visible: T[];
  hiddenCount: number;
}

export function resolveVizStyleTier(
  item: { path?: string; style_tier?: 'default' | 'variant' },
  pages: PageSummary[],
): 'default' | 'variant' | undefined {
  if (item.style_tier) return item.style_tier;
  if (!item.path) return undefined;
  const tplPage = pages.find((p) => p.path === item.path);
  if (!tplPage) return undefined;
  if (tplPage.style_tier) return tplPage.style_tier;
  if (tplPage.meta.type === 'template') return (tplPage.meta as TemplateMeta).style_tier;
  return undefined;
}

function vizSortRank(
  item: { status: Status; path?: string; style_tier?: 'default' | 'variant' },
  pages: PageSummary[],
): number {
  const tier = resolveVizStyleTier(item, pages);
  const ready = item.status === 'ready';
  if (tier === 'default') return ready ? 0 : 1;
  if (tier !== 'variant') return ready ? 2 : 3;
  return ready ? 4 : 5;
}

export function sortAndPartitionViz<T extends { status: Status; path?: string; style_tier?: 'default' | 'variant' }>(
  items: T[],
  pages: PageSummary[],
  expanded: boolean,
): PartitionedViz<T> {
  const sorted = [...items].sort((a, b) => vizSortRank(a, pages) - vizSortRank(b, pages));
  const defaultCount = sorted.filter((item) => resolveVizStyleTier(item, pages) === 'default').length;
  const collapsedLimit = sorted.length <= 3 ? sorted.length : Math.min(sorted.length, Math.max(3, defaultCount));
  const visible = expanded ? sorted : sorted.slice(0, collapsedLimit);
  const hiddenCount = Math.max(0, sorted.length - collapsedLimit);
  return { sorted, visible, hiddenCount };
}

export interface VizSlotGroup<T> {
  slotKey: string;
  primaryChart: string;
  items: T[];
  defaultItem: T;
}

export function groupVizBySlot<
  T extends {
    id: string;
    title: string;
    path: string;
    kind?: string;
    status: Status;
    chart_types?: string[];
    primary_method?: string;
    style_tier?: 'default' | 'variant';
    journal_style?: string;
  },
>(items: T[], pages: PageSummary[], fallbackMethodId: string): VizSlotGroup<T>[] {
  const buckets = new Map<string, { primaryChart: string; items: T[] }>();
  for (const item of items) {
    const tplPage = pages.find((p) => p.path === item.path);
    const tplMeta = tplPage?.meta.type === 'template' ? (tplPage.meta as TemplateMeta) : undefined;
    const isRecipe = item.kind === 'recipe' || tplPage?.meta.type === 'recipe';
    const ct = (item.chart_types?.[0] ?? tplMeta?.chart_types?.[0] ?? '').trim();
    const pm = (item.primary_method ?? tplMeta?.primary_method ?? fallbackMethodId).trim();
    const slotKey = !isRecipe && ct && pm ? `${pm}::${ct}` : `single::${item.path}`;
    let bucket = buckets.get(slotKey);
    if (!bucket) {
      bucket = { primaryChart: ct, items: [] };
      buckets.set(slotKey, bucket);
    }
    bucket.items.push(item);
  }
  const rank = (item: T): [number, number, string] => {
    const tier = resolveVizStyleTier(item, pages);
    const tierRank = tier === 'default' ? 0 : tier !== 'variant' ? 1 : 2;
    const statusRank = item.status === 'ready' ? 0 : 1;
    return [tierRank, statusRank, item.id];
  };
  const groups: VizSlotGroup<T>[] = [];
  for (const [slotKey, bucket] of buckets.entries()) {
    const sorted = [...bucket.items].sort((a, b) => {
      const [ta, sa, ia] = rank(a);
      const [tb, sb, ib] = rank(b);
      return ta - tb || sa - sb || ia.localeCompare(ib);
    });
    groups.push({
      slotKey,
      primaryChart: bucket.primaryChart,
      items: sorted,
      defaultItem: sorted[0],
    });
  }
  groups.sort((a, b) => vizSortRank(a.defaultItem, pages) - vizSortRank(b.defaultItem, pages));
  return groups;
}

function VizSlotSwitcher<
  T extends {
    id: string;
    title: string;
    path: string;
    style_tier?: 'default' | 'variant';
    journal_style?: string;
  },
>({
  group,
  activeId,
  pages,
  onSelect,
}: {
  group: VizSlotGroup<T>;
  activeId: string;
  pages: PageSummary[];
  onSelect: (id: string) => void;
}) {
  if (group.items.length <= 1) return null;
  const subjects = group.items.map((it) => {
    const tplPage = pages.find((p) => p.path === it.path);
    const tplMeta = tplPage?.meta.type === 'template' ? (tplPage.meta as TemplateMeta) : undefined;
    return {
      id: it.id,
      title: it.title,
      style_tier: it.style_tier ?? tplMeta?.style_tier ?? tplPage?.style_tier,
      journal_style: it.journal_style ?? tplMeta?.journal_style ?? tplPage?.journal_style,
    };
  });
  return (
    <div className="slot-style-switcher" role="group" aria-label={`切换 ${group.primaryChart || '模板'} 期刊画风`}>
      <span className="slot-switcher-label">期刊画风 ({group.items.length})</span>
      <div className="slot-switcher-pills">
        {group.items.map((variant, idx) => {
          const isSelected = variant.id === activeId;
          return (
            <button
              key={variant.id}
              type="button"
              className={isSelected ? 'slot-pill active' : 'slot-pill'}
              aria-pressed={isSelected}
              onClick={() => onSelect(variant.id)}
              title={`${variant.title} (${variant.id})`}
            >
              {stylePillLabel(subjects[idx], subjects)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function VizTierHeader({
  title,
  hiddenCount,
  expanded,
  onToggle,
}: {
  title: string;
  hiddenCount: number;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="method-ref-recipes-head viz-tier-head">
      <h3 className="viz-tier-heading">{title}</h3>
      {hiddenCount > 0 && (
        <button
          type="button"
          className="button small viz-variant-toggle"
          onClick={onToggle}
          aria-expanded={expanded}
        >
          {expanded ? '收起其余模板' : `展开其余 ${hiddenCount} 套绘图模板`}
        </button>
      )}
    </div>
  );
}

function CuratedVizCard({
  item,
  pages,
  onOpenStudio,
  slotSwitcher,
}: {
  item: AttachedVizCurated;
  pages: PageSummary[];
  onOpenStudio?: (id: string, title?: string) => void;
  slotSwitcher?: React.ReactNode;
}) {
  const tplPage = pages.find((p) => p.path === item.path);
  const resolvedLicense = item.license ?? (tplPage?.meta as { license?: string } | undefined)?.license;
  const compatLabel =
    item.compatibility === 'unreviewed'
      ? '待语义审查'
      : item.compatibility === 'curated'
        ? '方法配套'
        : COMPATIBILITY_LABEL[item.compatibility as keyof typeof COMPATIBILITY_LABEL] ?? item.compatibility;
  const thumbSrc = withThumbWidth(item.preview_url, 600) ?? item.preview_url;

  return (
    <article className="sheet viz-layer-card">
      <a className="viz-card-preview" {...pageLink(item.path)}>
        {thumbSrc ? (
          <img src={thumbSrc} alt={item.title} loading="lazy" />
        ) : tplPage ? (
          <FigureImage meta={tplPage.meta} thumbWidth={600} />
        ) : (
          <span className="preview-empty">暂无预览图</span>
        )}
      </a>
      <div className="viz-card-body">
        <div className="viz-card-badges">
          {item.primary && <span className="badge primary-mark">首选主关联</span>}
          <StatusBadge status={item.status} label={item.status === 'ready' ? '图模板可用' : undefined} />
          <StyleTierBadges styleTier={item.style_tier} journalStyle={item.journal_style} tplPage={tplPage} />
          {!!tplPage?.paper_origins?.length && <span className="cross-paper-badge">跨论文复用示例</span>}
          <span className={`compatibility compatibility-${item.compatibility}`}>{compatLabel}</span>
          {resolvedLicense && <LicenseBadge license={resolvedLicense} />}
          {item.language && <span className={`lang-pill lang-${item.language.toLowerCase()}`}>{item.language.toUpperCase()}</span>}
        </div>
        <h4><a {...pageLink(item.path)}>{item.title}</a></h4>
        <p className="small muted"><code>{item.id}</code>{item.chart_types.length > 0 && ` · ${item.chart_types.join(', ')}`}</p>
        {item.tables.length > 0 && (
          <p className="small muted">
            输入契约：{item.tables.map((t) => `${t.key}${t.interface ? ` (${t.interface})` : ''}`).join('、')}
          </p>
        )}
        {item.reason && <p className="small">{item.reason}</p>}
        {item.adaptation && <p className="small adaptation-note"><b>使用前需准备：</b>{item.adaptation}</p>}
        <p className="muted small">分析到绘图：{verificationLabel(item.verification)}</p>
        {slotSwitcher}
        <TemplateActionBar templateId={item.id} templateTitle={item.title} paperWorkflowId={tplPage?.paper_origins?.[0]?.workflow_id} onOpenStudio={onOpenStudio} />
      </div>
    </article>
  );
}

function CompatibleVizCard({
  item,
  pages,
  onOpenStudio,
  slotSwitcher,
}: {
  item: AttachedVizCompatible;
  pages: PageSummary[];
  onOpenStudio?: (id: string, title?: string) => void;
  slotSwitcher?: React.ReactNode;
}) {
  const tplPage = pages.find((p) => p.path === item.path);
  const thumbSrc = withThumbWidth(item.preview_url, 600) ?? item.preview_url;
  return (
    <article className="sheet viz-layer-card">
      <a className="viz-card-preview" {...pageLink(item.path)}>
        {thumbSrc ? (
          <img src={thumbSrc} alt={item.title} loading="lazy" />
        ) : (
          <span className="preview-empty">暂无预览图</span>
        )}
      </a>
      <div className="viz-card-body">
        <div className="viz-card-badges">
          <StatusBadge status={item.status} label={item.status === 'ready' ? '图模板可用' : undefined} />
          <StyleTierBadges styleTier={item.style_tier} journalStyle={item.journal_style} tplPage={tplPage} />
          {!!tplPage?.paper_origins?.length && <span className="cross-paper-badge">跨论文复用示例</span>}
          <span className={`match-pill match-${item.match_type}`}>
            {item.match_type === 'full' ? '完整对象直连 (full)' : '部分对象兼容 (partial)'}
          </span>
          {item.language && <span className={`lang-pill lang-${item.language.toLowerCase()}`}>{item.language.toUpperCase()}</span>}
        </div>
        <h4><a {...pageLink(item.path)}>{item.title}</a></h4>
        <p className="small muted"><code>{item.id}</code></p>
        {item.matched_interfaces.length > 0 && (
          <p className="small">匹配接口：<code>{item.matched_interfaces.join('、')}</code></p>
        )}
        {item.missing_required_interfaces.length > 0 && (
          <p className="small adaptation-note"><b>缺必需接口：</b><code>{item.missing_required_interfaces.join('、')}</code></p>
        )}
        {slotSwitcher}
        <TemplateActionBar templateId={item.id} templateTitle={item.title} paperWorkflowId={tplPage?.paper_origins?.[0]?.workflow_id} onOpenStudio={onOpenStudio} />
      </div>
    </article>
  );
}

function BridgedVizCard({
  item,
  pages,
  onOpenStudio,
  slotSwitcher,
}: {
  item: AttachedVizBridged;
  pages: PageSummary[];
  onOpenStudio?: (id: string, title?: string) => void;
  slotSwitcher?: React.ReactNode;
}) {
  const tplPage = pages.find((p) => p.path === item.path);
  const thumbSrc = withThumbWidth(item.preview_url, 600) ?? item.preview_url;
  return (
    <article className="sheet viz-layer-card bridged">
      <a className="viz-card-preview" {...pageLink(item.path)}>
        {thumbSrc ? (
          <img src={thumbSrc} alt={item.title} loading="lazy" />
        ) : (
          <span className="preview-empty">暂无预览图</span>
        )}
      </a>
      <div className="viz-card-body">
        <div className="viz-card-badges">
          <StatusBadge status={item.status} label={item.status === 'ready' ? '图模板可用' : undefined} />
          <StyleTierBadges styleTier={item.style_tier} journalStyle={item.journal_style} tplPage={tplPage} />
          {!!tplPage?.paper_origins?.length && <span className="cross-paper-badge">跨论文复用示例</span>}
          <span className="bridge-badge">经抽取表转换 (render_bridge)</span>
          <span className={`match-pill match-${item.match_type}`}>{item.match_type}</span>
        </div>
        <h4><a {...pageLink(item.path)}>{item.title}</a></h4>
        <p className="small muted"><code>{item.id}</code></p>
        <div className="bridge-extraction-box small">
          <strong>抽取转换步骤：</strong>
          <code>{item.from_output || '上游分析输出'}</code> → <code>{item.via_bridge}</code>
          {item.unit && <span className="muted"> · 单位：{item.unit}</span>}
          {item.extractor_note && <p className="small">{item.extractor_note}</p>}
        </div>
        {slotSwitcher}
        <TemplateActionBar templateId={item.id} templateTitle={item.title} paperWorkflowId={tplPage?.paper_origins?.[0]?.workflow_id} onOpenStudio={onOpenStudio} />
      </div>
    </article>
  );
}

/** Analysis workstation: 5 structured sections preserving per-branch verification and contract boundaries. */
export function MethodOverview({
  meta,
  purposeHtml,
  implementationStatus = [],
  figures,
  pages,
  hiddenSources,
  hub,
  nextSteps,
  onOpenStudio,
}: Props) {
  const [selectedIface, setSelectedIface] = useState<string>('');
  const [copiedNextCli, setCopiedNextCli] = useState(false);
  const [showAllCurated, setShowAllCurated] = useState(false);
  const [showAllCompatible, setShowAllCompatible] = useState(false);
  const [showAllBridged, setShowAllBridged] = useState(false);
  const [showAllFallback, setShowAllFallback] = useState(false);
  const [selectedBySlot, setSelectedBySlot] = useState<Record<string, string>>({});

  const inputSlugs = hub?.inputs ?? meta.inputs ?? [];
  const outputSlugs = hub?.outputs ?? meta.outputs ?? [];
  const contractSlugs = [...new Set([...inputSlugs, ...outputSlugs])];
  const definitions = contractSlugs.flatMap((slug) => {
    const found = pages.find((page) => page.path === `interfaces/${slug}.md`)?.meta;
    return found?.type === 'interface' ? [found as InterfaceMeta] : [];
  });
  const activeIfaceDef = definitions.find((d) => d.slug === selectedIface) ?? null;
  const optionalFields = definitions.flatMap((definition) =>
    Object.entries(definition.columns)
      .filter(([, column]) => column.required === false)
      .map(([name]) => `${definition.slug}.${name}`),
  );

  const domains = hub?.data_domains ?? domainsForMeta(meta);
  const purposes = hub?.purposes ?? meta.purposes ?? [];
  const effectiveImplStatus = hub?.implementation_status?.length ? hub.implementation_status : implementationStatus;

  const rawCurated = hub?.attached_visualizations.curated ?? [];
  const rawCuratedIds = new Set(rawCurated.map((c) => c.id));
  const mergedFallback: AttachedVizCurated[] = (hub?.reference_recipes ?? [])
    .filter((rec) => !rawCuratedIds.has(rec.id))
    .map((rec) => ({
      id: rec.id,
      title: rec.title,
      path: rec.path,
      kind: 'recipe',
      status: rec.status,
      language: rec.language,
      license: rec.license,
      chart_types: rec.chart_types ?? [],
      tables: [],
      preview_url: rec.preview_url,
      primary: true,
      compatibility: 'curated',
      verification: {
        state: rec.status === 'ready' ? 'verified' : 'not_run',
        scope: '方法映射配套模板',
        evidence: [],
      },
      reason: rec.note ?? '',
      adaptation: '',
      prerequisites: [],
    }));
  const curatedViz = [...rawCurated, ...mergedFallback];
  const curatedSlotGroups = groupVizBySlot(curatedViz, pages, meta.id);
  const curatedGroup = sortAndPartitionViz(curatedViz, pages, showAllCurated);
  const curatedDisplayGroups = showAllCurated
    ? curatedSlotGroups
    : curatedSlotGroups.slice(0, Math.max(3, curatedSlotGroups.filter((g) => resolveVizStyleTier(g.defaultItem, pages) === 'default').length));
  const curatedHiddenCount = Math.max(0, curatedSlotGroups.length - curatedDisplayGroups.length);

  const compatibleViz = hub?.attached_visualizations.object_compatible ?? [];
  const compatibleSlotGroups = groupVizBySlot(compatibleViz, pages, meta.id);
  const compatibleGroup = sortAndPartitionViz(compatibleViz, pages, showAllCompatible);
  const compatibleDisplayGroups = showAllCompatible
    ? compatibleSlotGroups
    : compatibleSlotGroups.slice(0, Math.max(3, compatibleSlotGroups.filter((g) => resolveVizStyleTier(g.defaultItem, pages) === 'default').length));
  const compatibleHiddenCount = Math.max(0, compatibleSlotGroups.length - compatibleDisplayGroups.length);

  const bridgedViz = hub?.attached_visualizations.render_bridged ?? [];
  const bridgedSlotGroups = groupVizBySlot(bridgedViz, pages, meta.id);
  const bridgedGroup = sortAndPartitionViz(bridgedViz, pages, showAllBridged);
  const bridgedDisplayGroups = showAllBridged
    ? bridgedSlotGroups
    : bridgedSlotGroups.slice(0, Math.max(3, bridgedSlotGroups.filter((g) => resolveVizStyleTier(g.defaultItem, pages) === 'default').length));
  const bridgedHiddenCount = Math.max(0, bridgedSlotGroups.length - bridgedDisplayGroups.length);
  const hasHubViz = curatedViz.length > 0 || compatibleViz.length > 0 || bridgedViz.length > 0;
  const fallbackFigures = hasHubViz ? [] : methodDisplayFigures(figures);
  const fallbackWrapped = fallbackFigures.map((f) => ({
    figure: f,
    status: f.meta.status,
    path: f.path,
    style_tier: f.meta.type === 'template' ? f.meta.style_tier : undefined,
  }));
  const fallbackGroup = sortAndPartitionViz(fallbackWrapped, pages, showAllFallback);

  const resolvedNext = nextSteps ?? hub?.next ?? null;
  const curatedBranches = resolvedNext?.curated_branches ?? [];
  const fallbackBranches = !curatedBranches.length ? (resolvedNext?.next_steps ?? meta.next_steps ?? []) : [];
  const objectCandidates = resolvedNext?.object_compatible_candidates ?? [];
  const nextCliCmd = `rwiki next ${meta.id} --json`;

  const renderIfacePills = (slugs: string[], kind: 'in' | 'out') =>
    slugs.map((slug) => {
      const path = `interfaces/${slug}.md`;
      const title = pages.find((p) => p.path === path)?.meta.title ?? slug;
      const isSelected = selectedIface === slug;
      return (
        <span key={slug} className={`contract-iface-chip ${kind}${isSelected ? ' selected' : ''}`}>
          <button
            type="button"
            className="contract-iface-btn"
            onClick={() => setSelectedIface(isSelected ? '' : slug)}
            title="点击查看列字段定义"
          >
            <code>{slug}</code>
            <span>{title}</span>
          </button>
          <a className="contract-iface-link" {...pageLink(path)} title={`打开接口页 ${slug}`}>↗</a>
        </span>
      );
    });

  return (
    <section className="method-overview method-workstation">
      <div className="method-workstation-tags">
        <span className="method-kind badge">{methodKindLabel(meta)}</span>
        {domains.map((slug) => (
          <span key={slug} className="domain-pill">{domainLabel(slug)}</span>
        ))}
        {purposes.map((p) => (
          <span key={p} className="purpose-pill">{p}</span>
        ))}
      </div>

      {/* Section 1: 方法概览 & 输入/输出对象契约栏 */}
      {purposeHtml && (
        <section className="method-purpose">
          <h2>研究问题与用途</h2>
          <div className="prose" dangerouslySetInnerHTML={{ __html: purposeHtml }} />
        </section>
      )}

      <section className="method-contract-bar sheet" aria-label="输入与输出对象契约">
        <div className="method-data-grid">
          <div className="contract-col">
            <h2>输入对象</h2>
            <p className="small">{meta.data_contract?.input || '见正文输入说明；标准接口不能代替模型、数据粒度与科学前提。'}</p>
            {inputSlugs.length > 0 && (
              <div className="contract-pill-group">
                <b className="small">读取接口</b>
                <div className="contract-pills">{renderIfacePills(inputSlugs, 'in')}</div>
              </div>
            )}
          </div>
          <div className="contract-arrow-col" aria-hidden="true">→</div>
          <div className="contract-col">
            <h2>输出对象</h2>
            <p className="small">{meta.data_contract?.output || '见正文输出说明，尚未提供对象契约。'}</p>
            {outputSlugs.length > 0 && (
              <div className="contract-pill-group">
                <b className="small">整理为接口</b>
                <div className="contract-pills">{renderIfacePills(outputSlugs, 'out')}</div>
              </div>
            )}
          </div>
        </div>

        {activeIfaceDef && (
          <div className="inline-iface-inspector" role="region" aria-label={`接口 ${activeIfaceDef.slug} 字段契约`}>
            <div className="inline-iface-head">
              <div>
                <strong>{activeIfaceDef.title}</strong> <code>{activeIfaceDef.slug}.csv</code>
              </div>
              <div className="inline-iface-actions">
                <a className="small" {...pageLink(`interfaces/${activeIfaceDef.slug}.md`)}>打开完整接口页</a>
                <button type="button" className="ghost small" onClick={() => setSelectedIface('')}>收起</button>
              </div>
            </div>
            <table className="input-columns">
              <thead><tr><th>字段</th><th>类型</th><th>必需</th><th>含义</th></tr></thead>
              <tbody>
                {Object.entries(activeIfaceDef.columns).map(([name, column]) => (
                  <tr key={name}>
                    <td><code>{name}</code></td>
                    <td>{column.type}</td>
                    <td>{column.required === false ? '可选' : '必需'}</td>
                    <td>{column.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <details className="method-details method-input-contract">
          <summary>内部表格式与可选字段（含 --bindings 映射约定）</summary>
          <p className="small">
            外部数据不必改名或改列名：用 <code>wiki.py render &lt;模板&gt; --data &lt;数据目录&gt; --bindings &lt;bindings.json&gt;</code>
            显式对应内部字段与作者列。不给 bindings 时仍读取标准 <code>&lt;接口&gt;.csv</code>；那只是执行约定，不是对原表的要求。
          </p>
          <ol className="small">
            <li>先核对数据语义、行单位、配对关系与量纲；字段名相同不代表这些已确认。</li>
            <li>在 bindings 的 <code>columns</code> 写“内部字段 → 作者列”；只做字段映射和无聚合的长宽整理。</li>
            <li>运行后查看输出目录的映射报告：源文件哈希、映射、缺失可选项和检查结果。</li>
            <li>bindings 不验证单位，也不自动做 0–1 / 0–100 换算；不明单位先停下来核对。</li>
          </ol>
          {optionalFields.length > 0 && (
            <p className="small"><b>实现允许缺省的可选字段：</b>{optionalFields.join('、')}（只有核心确实按缺省分支处理时才会列在这里）。</p>
          )}
          {definitions.length === 0 ? (
            <p className="muted small">本方法未声明内部接口；对象语义以“输入对象/输出对象”为准。</p>
          ) : (
            definitions.map((definition) => (
              <section key={definition.slug} className="input-definition">
                <h3><a {...pageLink(`interfaces/${definition.slug}.md`)}>{definition.title}</a> <code>{definition.slug}.csv</code></h3>
                <table className="input-columns">
                  <thead><tr><th>字段</th><th>类型</th><th>必需</th><th>含义</th></tr></thead>
                  <tbody>
                    {Object.entries(definition.columns).map(([name, column]) => (
                      <tr key={name}>
                        <td><code>{name}</code></td>
                        <td>{column.type}</td>
                        <td>{column.required === false ? '可选' : '必需'}</td>
                        <td>{column.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            ))
          )}
        </details>
      </section>

      {/* Section 2: 配套可视化模板（三层分类） */}
      <section className="method-viz-layers" aria-label="配套可视化模板">
        <div className="section-head-row">
          <div>
            <h2>配套可视化模板（三层兼容分类）</h2>
            <p className="muted small">
              图模板可用 ≠ 分析方法已验证可运行；同一图样按语义关联、对象直连与抽取表转换分层展示，并支持在当前页打开内联工作台定制参数与试跑。
            </p>
          </div>
        </div>

        {hasHubViz ? (
          <div className="viz-tier-stack">
            {curatedGroup.sorted.length > 0 && (
              <div className="viz-tier-group">
                <VizTierHeader
                  title={`1. 首选 / 语义关联 (${curatedGroup.sorted.length})`}
                  hiddenCount={curatedHiddenCount}
                  expanded={showAllCurated}
                  onToggle={() => setShowAllCurated((v) => !v)}
                />
                <div className="viz-layer-grid">
                  {curatedDisplayGroups.map((group) => {
                    const selectedId = selectedBySlot[`curated::${group.slotKey}`];
                    const active = group.items.find((x) => x.id === selectedId) ?? group.defaultItem;
                    return (
                      <CuratedVizCard
                        key={group.slotKey}
                        item={active}
                        pages={pages}
                        onOpenStudio={onOpenStudio}
                        slotSwitcher={
                          <VizSlotSwitcher
                            group={group}
                            activeId={active.id}
                            pages={pages}
                            onSelect={(id) => setSelectedBySlot((prev) => ({ ...prev, [`curated::${group.slotKey}`]: id }))}
                          />
                        }
                      />
                    );
                  })}
                </div>
              </div>
            )}

            {compatibleGroup.sorted.length > 0 && (
              <div className="viz-tier-group">
                <VizTierHeader
                  title={`2. 对象直连兼容 (full / partial · ${compatibleGroup.sorted.length})`}
                  hiddenCount={compatibleHiddenCount}
                  expanded={showAllCompatible}
                  onToggle={() => setShowAllCompatible((v) => !v)}
                />
                <div className="viz-layer-grid">
                  {compatibleDisplayGroups.map((group) => {
                    const selectedId = selectedBySlot[`compat::${group.slotKey}`];
                    const active = group.items.find((x) => x.id === selectedId) ?? group.defaultItem;
                    return (
                      <CompatibleVizCard
                        key={group.slotKey}
                        item={active}
                        pages={pages}
                        onOpenStudio={onOpenStudio}
                        slotSwitcher={
                          <VizSlotSwitcher
                            group={group}
                            activeId={active.id}
                            pages={pages}
                            onSelect={(id) => setSelectedBySlot((prev) => ({ ...prev, [`compat::${group.slotKey}`]: id }))}
                          />
                        }
                      />
                    );
                  })}
                </div>
              </div>
            )}

            {bridgedGroup.sorted.length > 0 && (
              <div className="viz-tier-group">
                <VizTierHeader
                  title={`3. 经抽取表转换 (render_bridge · ${bridgedGroup.sorted.length})`}
                  hiddenCount={bridgedHiddenCount}
                  expanded={showAllBridged}
                  onToggle={() => setShowAllBridged((v) => !v)}
                />
                <div className="viz-layer-grid">
                  {bridgedDisplayGroups.map((group) => {
                    const selectedId = selectedBySlot[`bridged::${group.slotKey}`];
                    const active = group.items.find((x) => x.id === selectedId) ?? group.defaultItem;
                    return (
                      <BridgedVizCard
                        key={group.slotKey}
                        item={active}
                        pages={pages}
                        onOpenStudio={onOpenStudio}
                        slotSwitcher={
                          <VizSlotSwitcher
                            group={group}
                            activeId={active.id}
                            pages={pages}
                            onSelect={(id) => setSelectedBySlot((prev) => ({ ...prev, [`bridged::${group.slotKey}`]: id }))}
                          />
                        }
                      />
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ) : fallbackGroup.sorted.length > 0 ? (
          <div className="viz-tier-group">
            {fallbackGroup.hiddenCount > 0 && (
              <div className="method-ref-recipes-head viz-tier-head">
                <span className="muted small">已优先展示主推默认图样（共 {fallbackGroup.sorted.length} 个）</span>
                <button
                  type="button"
                  className="button small viz-variant-toggle"
                  onClick={() => setShowAllFallback((v) => !v)}
                  aria-expanded={showAllFallback}
                >
                  {showAllFallback ? '收起变体' : `展开其余 ${fallbackGroup.hiddenCount} 套顶刊画风变体`}
                </button>
              </div>
            )}
            <div className="method-figure-grid">
              {fallbackGroup.visible.map(({ figure: f }) => (
              <article key={f.path} className="method-visual">
                <a className="method-figure-link" {...pageLink(f.path)}>
                  <span className="plate"><FigureImage meta={f.meta} /></span>
                  <strong>{f.meta.title}</strong>
                </a>
                <div className="method-visual-badges">
                  <StatusBadge status={f.meta.status} label={methodFigureStatusLabel(f)} />
                  {f.meta.type === 'template' && (
                    <StyleTierBadges styleTier={f.meta.style_tier} journalStyle={f.meta.journal_style} />
                  )}
                  <span className={`compatibility compatibility-${f.semantic?.compatibility ?? 'candidate'}`}>
                    {f.semantic ? COMPATIBILITY_LABEL[f.semantic.compatibility] : f.relation === 'reference' ? '参考图样' : '仅结构匹配'}
                  </span>
                </div>
                {f.semantic && (
                  <>
                    <p className="small">{f.semantic.reason}</p>
                    {f.semantic.compatibility === 'adaptable' && (
                      <p className="small adaptation-note"><b>使用前需准备：</b>{f.semantic.adaptation}</p>
                    )}
                    <p className="muted small">分析到绘图：{verificationLabel(f.semantic.verification)}</p>
                  </>
                )}
                {f.meta.type === 'template' && (
                  <p className="muted small source-note">{templateSourceNote(f.meta, pages, hiddenSources)}</p>
                )}
                {f.meta.type === 'template' && (
                  <TemplateActionBar templateId={f.meta.id} templateTitle={f.meta.title} onOpenStudio={onOpenStudio} />
                )}
              </article>
              ))}
            </div>
          </div>
        ) : (
          <p className="muted small">暂无已挂载的可视化模板；可查阅理论说明或通过多路下游分支探索。</p>
        )}
      </section>

      {/* Section 3: 做完此分析后的多重可选下游方向（Human & Agent Multi-Branch） */}
      <section className="method-next-branches" aria-label="多重可选下游方向">
        <div className="section-head-row">
          <div>
            <h2>做完此分析后的多重可选下游方向</h2>
            <p className="small muted">
              {resolvedNext?.agent_guidance || '下游分支均为可选科研决策，无固定线性顺序；请结合课题假设与中间表契约选择分支。'}
            </p>
          </div>
          <div className="next-cli-chip">
            <code>{nextCliCmd}</code>
            <button
              type="button"
              className="button small"
              onClick={() => {
                const write = navigator.clipboard?.writeText(nextCliCmd);
                if (!write) return;
                void write
                  .then(() => {
                    setCopiedNextCli(true);
                    setTimeout(() => setCopiedNextCli(false), 2000);
                  })
                  .catch(() => setCopiedNextCli(false));
              }}
            >
              {copiedNextCli ? '已复制' : '复制 Agent 命令'}
            </button>
          </div>
        </div>

        {curatedBranches.length > 0 ? (
          <div className="branch-grid">
            {curatedBranches.map((branch) => (
              <article key={branch.branch_id} className="sheet branch-card">
                <div className="branch-card-top">
                  <span className="branch-no">{branch.branch_id}</span>
                  <h3>{branch.direction}</h3>
                </div>
                {branch.when && (
                  <div className="branch-when">
                    <span className="branch-label">触发条件</span>
                    <p>{branch.when}</p>
                  </div>
                )}
                {branch.hypothesis && branch.hypothesis !== branch.when && (
                  <p className="small"><strong>研究假设：</strong>{branch.hypothesis}</p>
                )}
                {(branch.required_object || branch.produced_interface) && (
                  <p className="small muted">
                    {branch.required_object && <>输入对象：<code>{branch.required_object}</code></>}
                    {branch.required_object && branch.produced_interface && ' · '}
                    {branch.produced_interface && <>产物接口：<code>{branch.produced_interface}</code></>}
                  </p>
                )}
                {branch.next_methods.length > 0 && (
                  <div className="branch-templates">
                    <span className="branch-label">推荐下游分析方法</span>
                    <div className="branch-link-pills">
                      {branch.next_methods.map((m) => (
                        <a key={m.id} className="object-pill" {...pageLink(m.path)}>{m.title}</a>
                      ))}
                    </div>
                  </div>
                )}
                {branch.viz_templates.length > 0 && (
                  <div className="branch-viz">
                    <span className="branch-label">配套出图模板</span>
                    <div className="branch-viz-mini-list">
                      {branch.viz_templates.map((v) => (
                        <div key={v.id} className="branch-viz-mini">
                          <a {...pageLink(v.path)}>{v.title}</a>
                          <code>{v.id}</code>
                          {onOpenStudio ? (
                            <button type="button" className="button small" onClick={() => onOpenStudio(v.id, v.title)}>
                              定制/试跑
                            </button>
                          ) : (
                            <a className="button small" href={studioHref(v.id)}>工作台</a>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </article>
            ))}
          </div>
        ) : fallbackBranches.length > 0 ? (
          <div className="branch-grid">
            {fallbackBranches.map((step, idx) => (
              <article key={`${step.direction}:${idx}`} className="sheet branch-card">
                <div className="branch-card-top">
                  <span className="branch-no">分支 {idx + 1}</span>
                  <h3>{step.direction}</h3>
                </div>
                <p className="small">{step.when}</p>
                {step.intermediate_interface && (
                  <p className="small muted">标准中间表：<code>{step.intermediate_interface}</code></p>
                )}
              </article>
            ))}
          </div>
        ) : (
          <p className="small muted">当前方法尚未声明精选下游分支；可参考下方对象自动推导候选或前往 <a href="#/next">多路决策沙盘</a>。</p>
        )}

        {objectCandidates.length > 0 && (
          <details className="method-details">
            <summary>基于输出对象推导的兼容下游候选 ({objectCandidates.length} · 仅接口匹配，不代表语义已审查)</summary>
            <div className="candidate-grid">
              {objectCandidates.map((cand) => (
                <div key={`${cand.kind}:${cand.id}`} className="candidate-row">
                  <div>
                    <span className={`match-pill match-${cand.match_type}`}>{cand.match_type}</span>{' '}
                    <span className="badge">{cand.kind === 'method' ? '分析方法' : '图模板'}</span>{' '}
                    <a {...pageLink(cand.path)}>{cand.title}</a>{' '}
                    <code>{cand.id}</code>
                    <p className="small muted">
                      共享接口：{cand.shared_interfaces.join('、')}
                      {cand.missing_required_interfaces.length > 0 && ` · 缺必需接口：${cand.missing_required_interfaces.join('、')}`}
                    </p>
                  </div>
                  {cand.kind === 'template' && (
                    <a className="button small" href={studioHref(cand.id)}>打开工作台</a>
                  )}
                </div>
              ))}
            </div>
          </details>
        )}
      </section>

      {/* Section 4: 具体实现分支与逐分支验证收据 */}
      <MethodImplementations meta={meta} implementationStatus={effectiveImplStatus} />

      <p className="small"><a href={wikiFile(`methods/${meta.id}.md`)} target="_blank" rel="noreferrer">查看完整 Wiki 记录与来源元数据</a></p>
    </section>
  );
}

export function sortImplementations(implementations: MethodImplementation[]): MethodImplementation[] {
  const rank = (item: MethodImplementation): number => {
    if (item.impl_tier === 'default') return 0;
    if (item.impl_tier !== 'variant') return 1;
    return 2;
  };
  return implementations
    .map((item, idx) => ({ item, idx }))
    .sort((a, b) => rank(a.item) - rank(b.item) || a.idx - b.idx)
    .map(({ item }) => item);
}

export function implPillLabel(item: MethodImplementation, all: MethodImplementation[]): string {
  const base = item.modality?.trim()
    ? `${item.modality.trim()} · ${item.language}`
    : `${item.title} · ${item.language}`;
  const sameBaseCount = all.filter((peer) => {
    const peerBase = peer.modality?.trim()
      ? `${peer.modality.trim()} · ${peer.language}`
      : `${peer.title} · ${peer.language}`;
    return peerBase === base;
  }).length;
  const suffix = item.impl_tier === 'default' ? ' 默认' : '';
  return sameBaseCount > 1 ? `${base} (${item.id})${suffix}` : `${base}${suffix}`;
}

/** Runtime evidence is visible for technical/workflow code too, without analysis UI. */
export function MethodImplementations({ meta, implementationStatus = [] }: Pick<Props, 'meta' | 'implementationStatus'>) {
  const sortedImpls = sortImplementations(meta.implementations ?? []);
  const [selectedImplId, setSelectedImplId] = useState<string>(sortedImpls[0]?.id ?? '');
  const activeImpl = sortedImpls.find((item) => item.id === selectedImplId) ?? sortedImpls[0] ?? null;
  const activeStatus = activeImpl ? implementationStatus.find((s) => s.id === activeImpl.id) : undefined;
  const activeRuntime = activeStatus?.runtime;
  const activeState = activeStatus?.state ?? 'not_run';
  const activeDeps = activeRuntime?.declared
    ? (packageFacts(activeRuntime) || '未声明')
    : (activeImpl?.dependencies?.join('、') || '未声明额外依赖');
  const activeOptional = Object.entries(activeRuntime?.optional_packages ?? {}).flatMap(([language, packages]) =>
    Object.entries(packages).map(([name, purpose]) => `${language}:${name}（${purpose}）`),
  );

  return (
    <section className="method-code-implementations">
      <h2>具体实现与验证范围</h2>
      <p className="muted small">笔记确认与运行验证分别记录。验证仅覆盖所列分支、环境和检查范围；课题中仍需核对科学前提。</p>
      {sortedImpls.length > 0 && activeImpl ? (
        <>
          <div className="impl-switcher" role="group" aria-label="切换可执行实现分支">
            <span className="impl-switcher-label">可执行实现 ({sortedImpls.length})</span>
            <div className="impl-switcher-pills">
              {sortedImpls.map((impl) => {
                const isSelected = impl.id === activeImpl.id;
                return (
                  <button
                    key={impl.id}
                    type="button"
                    className={isSelected ? 'impl-pill active' : 'impl-pill'}
                    aria-pressed={isSelected}
                    data-impl-id={impl.id}
                    onClick={() => setSelectedImplId(impl.id)}
                    title={`${impl.title} (${impl.id})`}
                  >
                    {implPillLabel(impl, sortedImpls)}
                  </button>
                );
              })}
            </div>
          </div>

          <article className="sheet impl-active-card" aria-label={`当前实现 ${activeImpl.title}`}>
            <div className="impl-active-head">
              <div className="impl-active-title-row">
                <h3>{activeImpl.title}</h3>
                <code className="impl-id-code">{activeImpl.id}</code>
              </div>
              <div className="impl-active-badges">
                {activeImpl.impl_tier && (
                  <span className={`impl-tier-badge tier-${activeImpl.impl_tier}`}>
                    {activeImpl.impl_tier === 'default' ? '主推默认' : '场景变体'}
                  </span>
                )}
                {activeImpl.modality && <span className="modality-pill">{activeImpl.modality}</span>}
                {activeImpl.language && (
                  <span className={`lang-pill lang-${activeImpl.language.toLowerCase()}`}>{activeImpl.language}</span>
                )}
                {activeImpl.source_paper && (
                  <span className="source-paper-pill">源自 {activeImpl.source_paper}</span>
                )}
                <strong className={`implementation-state implementation-${activeState}`}>
                  {IMPLEMENTATION_LABEL[activeState] ?? '未运行'}
                </strong>
              </div>
            </div>

            <div className="impl-detail-grid">
              <div className="impl-detail-item">
                <span className="impl-detail-label">入口函数</span>
                <div className="impl-detail-value">
                  <code>{activeImpl.entrypoint}</code>
                  {entryKindLabel(activeRuntime) && (
                    <span className="muted small"> · {entryKindLabel(activeRuntime)}</span>
                  )}
                </div>
              </div>
              <div className="impl-detail-item">
                <span className="impl-detail-label">依赖包列表</span>
                <div className="impl-detail-value small">{activeDeps}</div>
              </div>
              <div className="impl-detail-item">
                <span className="impl-detail-label">运行方式与独立性</span>
                <div className="impl-detail-value small">
                  <strong className={`runtime-mode runtime-${activeRuntime?.mode ?? 'unknown'}`}>
                    {runtimeModeLabel(activeRuntime)}
                  </strong>
                  {' · '}
                  <span className={`portability portability-${activeRuntime?.portability?.state ?? 'unknown'}`}>
                    {portabilityLabel(activeRuntime)}
                  </span>
                  {!!conditionFacts(activeRuntime).length && (
                    <p className="small muted">运行条件（仅声明）：{conditionFacts(activeRuntime).join('；')}</p>
                  )}
                  {activeOptional.length > 0 && (
                    <p className="small muted">可选依赖：{activeOptional.join('、')}</p>
                  )}
                </div>
              </div>
              <div className="impl-detail-item">
                <span className="impl-detail-label">SHA256 验证收据与范围</span>
                <div className="impl-detail-value small">
                  <p className="small">{activeStatus?.scope || '未获得当前代码的有效验证范围。'}</p>
                  {activeImpl.verification && (
                    <a
                      className="small"
                      href={wikiFile(`methods/${meta.id}/${activeImpl.verification}`)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      查看算法验证收据 ({activeImpl.verification})
                    </a>
                  )}
                </div>
              </div>
            </div>
          </article>

          <details className="method-details method-impl-all-table">
            <summary>全部实现分支对比与独立验证范围 ({sortedImpls.length})</summary>
            <div className="method-implementation-scroll">
              <table className="method-implementations">
                <thead>
                  <tr><th>实现</th><th>入口</th><th>必要依赖（清单）</th><th>运行方式</th><th>验证与范围</th></tr>
                </thead>
                <tbody>
                  {sortedImpls.map((implementation) => {
                    const status = implementationStatus.find((s) => s.id === implementation.id);
                    const runtime = status?.runtime;
                    const state = status?.state ?? 'not_run';
                    const optional = Object.entries(runtime?.optional_packages ?? {}).flatMap(([language, packages]) =>
                      Object.entries(packages).map(([name, purpose]) => `${language}:${name}（${purpose}）`),
                    );
                    return (
                      <tr key={implementation.id}>
                        <td>
                          <strong>{implementation.title}</strong>
                          <span className="muted small">
                            {implementation.language}
                            {implementation.modality ? ` · ${implementation.modality}` : ''}
                            {implementation.impl_tier ? ` · ${implementation.impl_tier === 'default' ? '主推默认' : '场景变体'}` : ''}
                          </span>
                        </td>
                        <td><details><summary className="small">入口</summary><code>{implementation.entrypoint}</code></details></td>
                        <td>{runtime?.declared ? (packageFacts(runtime) || '未声明') : (implementation.dependencies?.join('、') || '未声明额外依赖')}</td>
                        <td>
                          <strong className={`runtime-mode runtime-${runtime?.mode ?? 'unknown'}`}>{runtimeModeLabel(runtime)}</strong>
                          <p className={`small portability portability-${runtime?.portability?.state ?? 'unknown'}`}>{portabilityLabel(runtime)}</p>
                          <details>
                            <summary className="small">复制清单、可选依赖与证据</summary>
                            <p className="small">复制：{runtime?.files?.length ? runtime.files.join('、') : '未声明清单'}</p>
                            {entryKindLabel(runtime) && <p className="small">入口类型：{entryKindLabel(runtime)}</p>}
                            {!!runtime?.resources?.length && <p className="small">资源：{runtime.resources.map((resource) => `${resource.path}（${resource.role}）`).join('、')}</p>}
                            {!!conditionFacts(runtime).length && <p className="small">运行条件（仅声明）：{conditionFacts(runtime).join('；')}</p>}
                            {optional.length > 0 && <p className="small">可选：{optional.join('、')}</p>}
                            {runtime?.portability?.evidence && <p className="small"><a href={wikiFile(`methods/${meta.id}/${runtime.portability.evidence}`)} target="_blank" rel="noreferrer">查看独立性证据</a></p>}
                            {!!runtime?.portability?.issues?.length && <p className="small error-text">{runtime.portability.issues.join('；')}</p>}
                          </details>
                        </td>
                        <td>
                          <strong className={`implementation-state implementation-${state}`}>{IMPLEMENTATION_LABEL[state] ?? '未运行'}</strong>
                          <details>
                            <summary className="small">范围与证据</summary>
                            <p className="small">{status?.scope || '未获得当前代码的有效验证范围。'}</p>
                            {implementation.verification && (
                              <a className="small" href={wikiFile(`methods/${meta.id}/${implementation.verification}`)} target="_blank" rel="noreferrer">查看算法验证收据</a>
                            )}
                          </details>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </details>
        </>
      ) : (
        <p className="notice small">尚未登记具体实现；可阅读方法判断，暂无已验证实现。</p>
      )}
    </section>
  );
}
