import { useState } from 'react';
import {
  AttachedVizBridged,
  AttachedVizCompatible,
  AttachedVizCurated,
  ImplementationStatus,
  InterfaceMeta,
  MethodHubDetail,
  MethodMeta,
  NextStepsResponse,
  PageSummary,
  studioHref,
  wikiFile,
} from '../api';
import { FigureImage, LicenseBadge, StatusBadge } from '../components';
import { MethodFigure, methodDisplayFigures, methodFigureStatusLabel, templateSourceNote } from '../figureModels';
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
  onOpenStudio,
}: {
  templateId: string;
  templateTitle: string;
  onOpenStudio?: (id: string, title?: string) => void;
}) {
  const [copied, setCopied] = useState(false);
  const cliCommand = `rwiki render ${templateId} --data <数据目录> --bindings <bindings.json>`;

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
    </div>
  );
}

function CuratedVizCard({
  item,
  pages,
  onOpenStudio,
}: {
  item: AttachedVizCurated;
  pages: PageSummary[];
  onOpenStudio?: (id: string, title?: string) => void;
}) {
  const tplPage = pages.find((p) => p.path === item.path);
  const compatLabel =
    item.compatibility === 'unreviewed'
      ? '待语义审查'
      : COMPATIBILITY_LABEL[item.compatibility as keyof typeof COMPATIBILITY_LABEL] ?? item.compatibility;

  return (
    <article className="sheet viz-layer-card">
      <a className="viz-card-preview" {...pageLink(item.path)}>
        {item.preview_url ? (
          <img src={item.preview_url} alt={item.title} loading="lazy" />
        ) : tplPage ? (
          <FigureImage meta={tplPage.meta} />
        ) : (
          <span className="preview-empty">暂无预览图</span>
        )}
      </a>
      <div className="viz-card-body">
        <div className="viz-card-badges">
          {item.primary && <span className="badge primary-mark">首选主关联</span>}
          <StatusBadge status={item.status} label={item.status === 'ready' ? '图模板可用' : undefined} />
          <span className={`compatibility compatibility-${item.compatibility}`}>{compatLabel}</span>
          {item.language && <span className={`lang-pill lang-${item.language.toLowerCase()}`}>{item.language.toUpperCase()}</span>}
        </div>
        <h4><a {...pageLink(item.path)}>{item.title}</a></h4>
        <p className="small muted"><code>{item.id}</code>{item.chart_types.length > 0 && ` · ${item.chart_types.join(', ')}`}</p>
        {item.reason && <p className="small">{item.reason}</p>}
        {item.adaptation && <p className="small adaptation-note"><b>使用前需准备：</b>{item.adaptation}</p>}
        <p className="muted small">分析到绘图：{verificationLabel(item.verification)}</p>
        <TemplateActionBar templateId={item.id} templateTitle={item.title} onOpenStudio={onOpenStudio} />
      </div>
    </article>
  );
}

function CompatibleVizCard({
  item,
  onOpenStudio,
}: {
  item: AttachedVizCompatible;
  onOpenStudio?: (id: string, title?: string) => void;
}) {
  return (
    <article className="sheet viz-layer-card">
      <a className="viz-card-preview" {...pageLink(item.path)}>
        {item.preview_url ? (
          <img src={item.preview_url} alt={item.title} loading="lazy" />
        ) : (
          <span className="preview-empty">暂无预览图</span>
        )}
      </a>
      <div className="viz-card-body">
        <div className="viz-card-badges">
          <StatusBadge status={item.status} label={item.status === 'ready' ? '图模板可用' : undefined} />
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
        <TemplateActionBar templateId={item.id} templateTitle={item.title} onOpenStudio={onOpenStudio} />
      </div>
    </article>
  );
}

function BridgedVizCard({
  item,
  onOpenStudio,
}: {
  item: AttachedVizBridged;
  onOpenStudio?: (id: string, title?: string) => void;
}) {
  return (
    <article className="sheet viz-layer-card bridged">
      <a className="viz-card-preview" {...pageLink(item.path)}>
        {item.preview_url ? (
          <img src={item.preview_url} alt={item.title} loading="lazy" />
        ) : (
          <span className="preview-empty">暂无预览图</span>
        )}
      </a>
      <div className="viz-card-body">
        <div className="viz-card-badges">
          <StatusBadge status={item.status} label={item.status === 'ready' ? '图模板可用' : undefined} />
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
        <TemplateActionBar templateId={item.id} templateTitle={item.title} onOpenStudio={onOpenStudio} />
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

  const curatedViz = hub?.attached_visualizations.curated ?? [];
  const compatibleViz = hub?.attached_visualizations.object_compatible ?? [];
  const bridgedViz = hub?.attached_visualizations.render_bridged ?? [];
  const hasHubViz = curatedViz.length > 0 || compatibleViz.length > 0 || bridgedViz.length > 0;
  const fallbackFigures = hasHubViz ? [] : methodDisplayFigures(figures);

  const resolvedNext = nextSteps ?? hub?.next ?? null;
  const curatedBranches = resolvedNext?.curated_branches ?? [];
  const fallbackBranches = !curatedBranches.length ? (resolvedNext?.next_steps ?? meta.next_steps ?? []) : [];
  const objectCandidates = resolvedNext?.object_compatible_candidates ?? [];
  const referenceRecipes = hub?.reference_recipes ?? [];
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
            {curatedViz.length > 0 && (
              <div className="viz-tier-group">
                <h3 className="viz-tier-heading">1. 首选 / 语义关联 ({curatedViz.length})</h3>
                <div className="viz-layer-grid">
                  {curatedViz.map((item) => (
                    <CuratedVizCard key={item.id} item={item} pages={pages} onOpenStudio={onOpenStudio} />
                  ))}
                </div>
              </div>
            )}

            {compatibleViz.length > 0 && (
              <div className="viz-tier-group">
                <h3 className="viz-tier-heading">2. 对象直连兼容 (full / partial · {compatibleViz.length})</h3>
                <div className="viz-layer-grid">
                  {compatibleViz.map((item) => (
                    <CompatibleVizCard key={item.id} item={item} onOpenStudio={onOpenStudio} />
                  ))}
                </div>
              </div>
            )}

            {bridgedViz.length > 0 && (
              <div className="viz-tier-group">
                <h3 className="viz-tier-heading">3. 经抽取表转换 (render_bridge · {bridgedViz.length})</h3>
                <div className="viz-layer-grid">
                  {bridgedViz.map((item) => (
                    <BridgedVizCard key={item.id} item={item} onOpenStudio={onOpenStudio} />
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : fallbackFigures.length > 0 ? (
          <div className="method-figure-grid">
            {fallbackFigures.map((f) => (
              <article key={f.path} className="method-visual">
                <a className="method-figure-link" {...pageLink(f.path)}>
                  <span className="plate"><FigureImage meta={f.meta} /></span>
                  <strong>{f.meta.title}</strong>
                </a>
                <div className="method-visual-badges">
                  <StatusBadge status={f.meta.status} label={methodFigureStatusLabel(f)} />
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
        ) : (
          <p className="muted small">暂无已挂载的可视化模板；可查阅下方理论说明或通过多路下游分支探索。</p>
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
                void navigator.clipboard?.writeText(nextCliCmd).then(() => {
                  setCopiedNextCli(true);
                  setTimeout(() => setCopiedNextCli(false), 2000);
                });
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

      {/* Section 5: 参考源码配方折叠栏 (FigureYa L1) */}
      <details className="method-details method-reference-recipes">
        <summary>参考源码配方（FigureYa L1 · {referenceRecipes.length}）</summary>
        {referenceRecipes.length === 0 ? (
          <p className="small muted">当前方法暂无已映射的参考源码配方。</p>
        ) : (
          <div className="reference-recipes-grid">
            {referenceRecipes.map((rec) => (
              <article key={rec.id} className="reference-recipe-item">
                {rec.preview_url && (
                  <a className="ref-recipe-thumb" {...pageLink(rec.path)}>
                    <img src={rec.preview_url} alt={rec.title} loading="lazy" />
                  </a>
                )}
                <div className="ref-recipe-meta">
                  <h4><a {...pageLink(rec.path)}>{rec.title}</a></h4>
                  <p className="small muted"><code>{rec.id}</code> · {rec.language.toUpperCase() || 'R'} · {rec.confidence}</p>
                  {rec.note && <p className="small">{rec.note}</p>}
                  <div className="ref-recipe-actions">
                    <LicenseBadge license="CC-BY-NC-SA-4.0" />
                    <a className="button small" {...pageLink(rec.path)}>查看配方</a>
                    <a className="button primary small" href={studioHref(rec.id)}>工作台</a>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </details>

      <p className="small"><a href={wikiFile(`methods/${meta.id}.md`)} target="_blank" rel="noreferrer">查看完整 Wiki 记录与来源元数据</a></p>
    </section>
  );
}

/** Runtime evidence is visible for technical/workflow code too, without analysis UI. */
export function MethodImplementations({ meta, implementationStatus = [] }: Pick<Props, 'meta' | 'implementationStatus'>) {
  return (
    <section className="method-code-implementations">
      <h2>具体实现与验证范围</h2>
      <p className="muted small">笔记确认与运行验证分别记录。验证仅覆盖所列分支、环境和检查范围；课题中仍需核对科学前提。</p>
      {meta.implementations?.length ? (
        <div className="method-implementation-scroll">
          <table className="method-implementations">
            <thead>
              <tr><th>实现</th><th>入口</th><th>必要依赖（清单）</th><th>运行方式</th><th>验证与范围</th></tr>
            </thead>
            <tbody>
              {meta.implementations.map((implementation) => {
                const status = implementationStatus.find((s) => s.id === implementation.id);
                const runtime = status?.runtime;
                const state = status?.state ?? 'not_run';
                const optional = Object.entries(runtime?.optional_packages ?? {}).flatMap(([language, packages]) =>
                  Object.entries(packages).map(([name, purpose]) => `${language}:${name}（${purpose}）`),
                );
                return (
                  <tr key={implementation.id}>
                    <td><strong>{implementation.title}</strong><span className="muted small">{implementation.language}</span></td>
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
      ) : (
        <p className="notice small">尚未登记具体实现；可阅读方法判断，暂无已验证实现。</p>
      )}
    </section>
  );
}
