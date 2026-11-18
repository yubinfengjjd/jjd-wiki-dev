import { useEffect, useMemo, useState } from 'react';
import {
  api,
  imageOf,
  InterfaceMeta,
  MethodMeta,
  NextStepBranch,
  NextStepsResponse,
  PageSummary,
  PlaybookItem,
  PlaybookStep,
  studioHref,
} from '../api';
import type { AppData } from '../App';
import { FigureImage, StatusBadge } from '../components';
import { pageLink } from '../nav';

const CORE_PLAYBOOK_META: Record<string, { title: string; subtitle: string; steps: PlaybookStep[] }> = {
  'scrna-stepwise-playbook': {
    title: '单细胞转录组步进决策树',
    subtitle: 'QC / 批次整合 → 细胞类型注释 → 六大下游探索分支',
    steps: [
      { id: 'cell-quality-control', title: 'Step 1 · 单细胞质量控制 (QC)', method_id: 'cell-quality-control', description: '线粒体/核糖体/双细胞过滤', next: ['batch-integration'] },
      { id: 'batch-integration', title: 'Step 2 · 批次效应整合与降维聚类', method_id: 'batch-integration', description: 'Harmony / Seurat Anchor / UMAP', next: ['cell-type-annotation'] },
      { id: 'cell-type-annotation', title: 'Step 3 · 细胞类型注释', method_id: 'cell-type-annotation', description: 'Marker 气泡图与参考映射；完成后展开 6 大下游方向', next: ['differential-expression', 'gene-set-scoring', 'trajectory-inference'] },
      { id: 'differential-expression', title: 'Step 4A · 亚群差异表达 & 富集', method_id: 'differential-expression', description: 'FindMarkers / pseudobulk DEG', next: ['gene-set-enrichment'] },
      { id: 'gene-set-scoring', title: 'Step 4B · 基因集多算法打分', method_id: 'gene-set-scoring', description: 'AUCell / UCell / ssGSEA', next: ['trajectory-inference'] },
      { id: 'trajectory-inference', title: 'Step 4C · 拟时序与动态基因', method_id: 'trajectory-inference', description: 'Monocle2/3 / Slingshot 轨迹分化', next: ['dynamic-feature-analysis', 'rna-velocity'] },
      { id: 'dynamic-feature-analysis', title: 'Step 5A · 动态分支热图', method_id: 'dynamic-feature-analysis', description: 'BEAM 分支基因动力学' },
      { id: 'rna-velocity', title: 'Step 5B · RNA 速率方向验证', method_id: 'rna-velocity', description: 'scVelo 矢量场验证' },
      { id: 'gene-set-enrichment', title: 'Step 5C · 通路富集气泡/GSEA', method_id: 'gene-set-enrichment', description: 'GO / KEGG / GSEA' },
    ],
  },
  'bulk-ml-biomarker-playbook': {
    title: 'Bulk + 101种机器学习标志物决策树',
    subtitle: '差异表达 / WGCNA → 候选交集 → 101种ML筛选 → SHAP解释 & 临床预后',
    steps: [
      { id: 'differential-expression', title: 'Step 1 · Bulk 差异表达分析', method_id: 'differential-expression', description: 'limma / DESeq2 / edgeR', next: ['gene-set-enrichment', 'shap-explanation'] },
      { id: 'gene-set-enrichment', title: 'Step 2 · 功能与通路富集', method_id: 'gene-set-enrichment', description: 'GO / KEGG / GSEA 生物学定位', next: ['shap-explanation'] },
      { id: 'shap-explanation', title: 'Step 3 · 机器学习特征筛选与 SHAP 解释', method_id: 'shap-explanation', description: '101 ML / LASSO / SVM / Boruta / SHAP 蜂群图', next: [] },
    ],
  },
  'geneset-theme-playbook': {
    title: '特定修饰/基因集主题挖掘决策树',
    subtitle: 'PTM / 乳酸化 / 代谢 / 铁死亡基因集 → 多算法打分 → 高活亚群深挖与分型',
    steps: [
      { id: 'gene-set-scoring', title: 'Step 1 · 主题基因集多算法打分', method_id: 'gene-set-scoring', description: 'AUCell / UCell / AddModuleScore / ssGSEA', next: ['differential-expression', 'trajectory-inference'] },
      { id: 'differential-expression', title: 'Step 2A · 高低活组差异基因', method_id: 'differential-expression', description: '筛选主题核心调控靶点', next: ['gene-set-enrichment'] },
      { id: 'trajectory-inference', title: 'Step 2B · 高活亚群拟时序演化', method_id: 'trajectory-inference', description: '追踪修饰/表型转折点', next: ['dynamic-feature-analysis'] },
      { id: 'gene-set-enrichment', title: 'Step 3A · 富集关联机制', method_id: 'gene-set-enrichment', description: '下游信号通路验证' },
      { id: 'dynamic-feature-analysis', title: 'Step 3B · 分支动态特征', method_id: 'dynamic-feature-analysis', description: '拟时序开关基因热图' },
    ],
  },
  'sc-bulk-integration-playbook': {
    title: '单细胞 × Bulk 多组学联合决策树',
    subtitle: '单细胞关键亚群注释 & Marker → 投射 Bulk 临床队列 → 标志物与 SHAP 解释',
    steps: [
      { id: 'cell-type-annotation', title: 'Step 1 · 锁定单细胞关键细胞亚群', method_id: 'cell-type-annotation', description: '识别疾病富集关键亚群', next: ['differential-expression', 'trajectory-inference'] },
      { id: 'differential-expression', title: 'Step 2 · 提取亚群特异性 Marker', method_id: 'differential-expression', description: '定义核心候选特征基因集', next: ['gene-set-scoring', 'shap-explanation'] },
      { id: 'trajectory-inference', title: 'Step 2B · 轨迹末端分化基因', method_id: 'trajectory-inference', description: '提取命运决定基因', next: ['shap-explanation'] },
      { id: 'gene-set-scoring', title: 'Step 3A · Bulk 队列单样本打分/反卷积', method_id: 'gene-set-scoring', description: 'ssGSEA / CIBERSORT 临床分组对比', next: ['shap-explanation'] },
      { id: 'shap-explanation', title: 'Step 4 · 预后/诊断模型与 SHAP 解释', method_id: 'shap-explanation', description: '构建多基因模型并输出风险与 SHAP 图' },
    ],
  },
};

const CORE_PLAYBOOK_ORDER = [
  'scrna-stepwise-playbook',
  'bulk-ml-biomarker-playbook',
  'geneset-theme-playbook',
  'sc-bulk-integration-playbook',
];

interface PositionedNode {
  step: PlaybookStep;
  col: number;
  row: number;
  x: number;
  y: number;
}

const NODE_W = 228;
const NODE_H = 82;
const COL_GAP = 72;
const ROW_GAP = 28;
const PAD_X = 28;
const PAD_Y = 28;

function layoutDag(steps: PlaybookStep[]): {
  nodes: PositionedNode[];
  edges: { from: PositionedNode; to: PositionedNode }[];
  width: number;
  height: number;
} {
  if (!steps.length) return { nodes: [], edges: [], width: 640, height: 220 };
  const byId = new Map(steps.map((s) => [s.id, s]));
  const depth = new Map<string, number>();

  // Longest-path topological layering so sequential pipelines flow cleanly left -> right.
  const computeDepth = (id: string, visiting: Set<string>): number => {
    if (depth.has(id)) return depth.get(id)!;
    if (visiting.has(id)) return 0;
    visiting.add(id);
    let maxParent = -1;
    for (const candidate of steps) {
      if ((candidate.next ?? []).includes(id) && candidate.id !== id) {
        maxParent = Math.max(maxParent, computeDepth(candidate.id, visiting));
      }
    }
    visiting.delete(id);
    const d = maxParent + 1;
    depth.set(id, d);
    return d;
  };

  for (let i = 0; i < steps.length; i++) {
    const s = steps[i];
    if (!steps.some((other) => (other.next ?? []).includes(s.id))) {
      // If no explicit `next` edges exist at all, lay out sequentially.
      const hasAnyEdges = steps.some((other) => (other.next ?? []).length > 0);
      depth.set(s.id, hasAnyEdges ? 0 : i);
    } else {
      computeDepth(s.id, new Set());
    }
  }

  const columns = new Map<number, PlaybookStep[]>();
  for (const s of steps) {
    const col = depth.get(s.id) ?? 0;
    columns.set(col, [...(columns.get(col) ?? []), s]);
  }

  const maxRows = Math.max(...[...columns.values()].map((c) => c.length), 1);
  const maxCol = Math.max(...[...columns.keys()], 0);
  const totalHeight = Math.max(240, PAD_Y * 2 + maxRows * NODE_H + (maxRows - 1) * ROW_GAP);
  const totalWidth = Math.max(680, PAD_X * 2 + (maxCol + 1) * NODE_W + maxCol * COL_GAP);

  const nodes: PositionedNode[] = [];
  const posById = new Map<string, PositionedNode>();

  for (const [col, colSteps] of [...columns.entries()].sort((a, b) => a[0] - b[0])) {
    const colHeight = colSteps.length * NODE_H + (colSteps.length - 1) * ROW_GAP;
    const startY = (totalHeight - colHeight) / 2;
    colSteps.forEach((step, row) => {
      const node: PositionedNode = {
        step,
        col,
        row,
        x: PAD_X + col * (NODE_W + COL_GAP),
        y: startY + row * (NODE_H + ROW_GAP),
      };
      nodes.push(node);
      posById.set(step.id, node);
    });
  }

  const edges: { from: PositionedNode; to: PositionedNode }[] = [];
  const hasExplicitEdges = steps.some((s) => (s.next ?? []).length > 0);
  if (hasExplicitEdges) {
    for (const s of steps) {
      const from = posById.get(s.id);
      if (!from) continue;
      for (const targetId of s.next ?? []) {
        if (!byId.has(targetId)) continue;
        const to = posById.get(targetId);
        if (to && to !== from) edges.push({ from, to });
      }
    }
  } else {
    for (let i = 0; i < nodes.length - 1; i++) {
      edges.push({ from: nodes[i], to: nodes[i + 1] });
    }
  }

  return { nodes, edges, width: totalWidth, height: totalHeight };
}

function normalizePlaybooks(rawPlaybooks: PlaybookItem[], pages: PageSummary[]): PlaybookItem[] {
  const byId = new Map<string, PlaybookItem>();
  for (const pb of rawPlaybooks) {
    const fallback = CORE_PLAYBOOK_META[pb.id];
    const steps = pb.steps?.length ? pb.steps : fallback?.steps ?? [];
    byId.set(pb.id, {
      ...pb,
      title: pb.title || fallback?.title || pb.id,
      summary: pb.summary || fallback?.subtitle || '',
      steps,
    });
  }
  for (const p of pages) {
    if (p.meta.type === 'scenario' && p.meta.id.includes('playbook') && !byId.has(p.meta.id)) {
      const fallback = CORE_PLAYBOOK_META[p.meta.id];
      byId.set(p.meta.id, {
        id: p.meta.id,
        title: p.meta.title || fallback?.title || p.meta.id,
        path: p.path,
        summary: p.meta.summary || fallback?.subtitle || '',
        tags: p.meta.tags,
        steps: fallback?.steps ?? [],
      });
    }
  }
  for (const id of CORE_PLAYBOOK_ORDER) {
    if (!byId.has(id)) {
      const fallback = CORE_PLAYBOOK_META[id];
      byId.set(id, {
        id,
        title: fallback.title,
        path: `scenarios/${id}.md`,
        summary: fallback.subtitle,
        steps: fallback.steps,
      });
    }
  }
  return [...byId.values()].sort((a, b) => {
    const ia = CORE_PLAYBOOK_ORDER.indexOf(a.id);
    const ib = CORE_PLAYBOOK_ORDER.indexOf(b.id);
    if (ia !== -1 && ib !== -1) return ia - ib;
    if (ia !== -1) return -1;
    if (ib !== -1) return 1;
    return a.title.localeCompare(b.title);
  });
}

function resolvePageById(id: string, pages: PageSummary[]): PageSummary | undefined {
  const clean = id.replace(/\.md$/, '').replace(/^(methods|templates|interfaces|recipes)\//, '');
  return pages.find((p) => {
    if (p.path === id || p.path === `${id}.md`) return true;
    if ('id' in p.meta && p.meta.id === clean) return true;
    if ('slug' in p.meta && p.meta.slug === clean) return true;
    return false;
  });
}

export function PlaybooksView({ data, query = '' }: { data: AppData; query?: string }) {
  const [serverPlaybooks, setServerPlaybooks] = useState<PlaybookItem[]>([]);
  const [selectedPlaybookId, setSelectedPlaybookId] = useState<string>(() => {
    const params = new URLSearchParams(query);
    return params.get('playbook') || 'scrna-stepwise-playbook';
  });
  const [selectedStepId, setSelectedStepId] = useState<string>(() => {
    const params = new URLSearchParams(query);
    return params.get('step') || 'cell-type-annotation';
  });
  const [nextResp, setNextResp] = useState<NextStepsResponse | null>(null);
  const [loadingNext, setLoadingNext] = useState(false);
  const [nextError, setNextError] = useState('');
  const [branchFilter, setBranchFilter] = useState('');

  useEffect(() => {
    let active = true;
    api.playbooks()
      .then((res) => {
        if (!active) return;
        const list = res.playbooks?.length ? res.playbooks : res.scenarios ?? [];
        setServerPlaybooks(list);
      })
      .catch(() => {
        // Fallback to local scenario pages & CORE_PLAYBOOK_META when offline in unit tests.
      });
    return () => { active = false; };
  }, []);

  const playbooks = useMemo(() => normalizePlaybooks(serverPlaybooks, data.pages), [serverPlaybooks, data.pages]);
  const activePlaybook = playbooks.find((p) => p.id === selectedPlaybookId) ?? playbooks[0];

  useEffect(() => {
    if (!activePlaybook?.steps.length) return;
    if (!activePlaybook.steps.some((s) => s.id === selectedStepId || s.method_id === selectedStepId)) {
      const preferred = activePlaybook.steps.find((s) => s.id === 'cell-type-annotation') ?? activePlaybook.steps[0];
      setSelectedStepId(preferred.id);
    }
  }, [activePlaybook, selectedStepId]);

  const activeStep = activePlaybook?.steps.find((s) => s.id === selectedStepId) ?? activePlaybook?.steps[0];
  const activeNodeId = activeStep?.method_id || activeStep?.id || selectedStepId;

  useEffect(() => {
    if (!activeNodeId) return;
    let active = true;
    setLoadingNext(true);
    setNextError('');
    api.nextSteps(activeNodeId, branchFilter)
      .then((res) => {
        if (!active) return;
        setNextResp(res);
        setLoadingNext(false);
      })
      .catch((err: Error) => {
        if (!active) return;
        // Fallback to frontmatter `next_steps` on matching method page if endpoint is unavailable
        const methodPage = resolvePageById(activeNodeId, data.pages);
        if (methodPage?.meta.type === 'method' && methodPage.meta.next_steps?.length) {
          setNextResp({
            node_id: activeNodeId,
            title: methodPage.meta.title,
            path: methodPage.path,
            next_steps: methodPage.meta.next_steps,
          });
          setNextError('');
        } else {
          setNextResp({ node_id: activeNodeId, next_steps: [] });
          setNextError(err.message);
        }
        setLoadingNext(false);
      });
    return () => { active = false; };
  }, [activeNodeId, branchFilter, data.pages]);

  const dag = useMemo(() => layoutDag(activePlaybook?.steps ?? []), [activePlaybook]);
  const connectedIds = useMemo(() => {
    const set = new Set<string>();
    if (!activeStep) return set;
    set.add(activeStep.id);
    for (const e of dag.edges) {
      if (e.from.step.id === activeStep.id) set.add(e.to.step.id);
      if (e.to.step.id === activeStep.id) set.add(e.from.step.id);
    }
    return set;
  }, [dag, activeStep]);

  const branches: NextStepBranch[] = nextResp?.next_steps ?? [];
  const filteredBranches = branchFilter.trim()
    ? branches.filter((b) =>
        `${b.direction} ${b.when} ${b.intermediate_interface} ${b.analysis_templates.join(' ')} ${b.viz_templates.join(' ')}`
          .toLowerCase()
          .includes(branchFilter.trim().toLowerCase()),
      )
    : branches;

  const activeMethodPage = resolvePageById(activeNodeId, data.pages);

  return (
    <section className="playbooks-workbench">
      <header className="hero slim">
        <div className="hero-text">
          <h1>步进决策导航</h1>
          <p className="lede">
            生信分析「走一步看一步」决策工作台：选择当前所处的分析阶段，查看有证据支持的下游分支、标准中间表契约、推荐分析模版与配套可视化预览图，一键进入代码模版操控台。
          </p>
        </div>
        <div className="playbook-quick-links">
          <a className="button primary" href="#/studio">直接打开代码操控台</a>
          <a className="button" href="#/projects">查看课题步进看板</a>
        </div>
      </header>

      <div className="playbook-tabs" role="tablist" aria-label="四大生信主线决策树">
        {playbooks.map((pb, idx) => (
          <button
            key={pb.id}
            type="button"
            role="tab"
            aria-selected={activePlaybook?.id === pb.id}
            className={activePlaybook?.id === pb.id ? 'playbook-tab active' : 'playbook-tab'}
            onClick={() => setSelectedPlaybookId(pb.id)}
          >
            <span className="playbook-tab-index">主线 {idx + 1}</span>
            <strong>{pb.title}</strong>
            {pb.summary && <small>{pb.summary}</small>}
          </button>
        ))}
      </div>

      {activePlaybook && (
        <section className="sheet dag-panel" aria-label="交互式步进决策流画布">
          <div className="dag-header">
            <div>
              <h2>{activePlaybook.title}</h2>
              <p className="small muted">
                点击画布中的任意分析步骤节点（如 <code>cell-type-annotation</code>），下方将展开该步骤的下游方向、中间表契约与可调用模版。
              </p>
            </div>
            <div className="dag-step-select">
              <label className="small">
                快速定位当前步骤：
                <select
                  aria-label="选择当前步骤"
                  value={activeStep?.id ?? ''}
                  onChange={(e) => setSelectedStepId(e.target.value)}
                >
                  {activePlaybook.steps.map((s) => (
                    <option key={s.id} value={s.id}>{s.title}</option>
                  ))}
                </select>
              </label>
              {resolvePageById(activePlaybook.path, data.pages) && (
                <a className="button small" {...pageLink(activePlaybook.path)}>查看 Playbook 文档</a>
              )}
            </div>
          </div>

          <div className="dag-scroll">
            <div className="dag-canvas" style={{ width: dag.width, height: dag.height }}>
              <svg className="dag-edges" width={dag.width} height={dag.height} aria-hidden="true">
                <defs>
                  <marker id="dag-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                    <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--line)" />
                  </marker>
                  <marker id="dag-arrow-active" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                    <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--hub)" />
                  </marker>
                </defs>
                {dag.edges.map(({ from, to }) => {
                  const x1 = from.x + NODE_W;
                  const y1 = from.y + NODE_H / 2;
                  const x2 = to.x;
                  const y2 = to.y + NODE_H / 2;
                  const dx = Math.max(36, (x2 - x1) * 0.5);
                  const isActive = from.step.id === activeStep?.id || to.step.id === activeStep?.id;
                  return (
                    <path
                      key={`${from.step.id}->${to.step.id}`}
                      d={`M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2 - 4} ${y2}`}
                      className={isActive ? 'dag-edge active' : 'dag-edge'}
                      markerEnd={isActive ? 'url(#dag-arrow-active)' : 'url(#dag-arrow)'}
                    />
                  );
                })}
              </svg>

              {dag.nodes.map(({ step, x, y }) => {
                const isSelected = activeStep?.id === step.id;
                const isNeighbor = !isSelected && connectedIds.has(step.id);
                const methodId = step.method_id || step.id;
                return (
                  <button
                    key={step.id}
                    type="button"
                    style={{ left: x, top: y, width: NODE_W, height: NODE_H }}
                    className={`dag-node${isSelected ? ' selected' : ''}${isNeighbor ? ' neighbor' : ''}`}
                    onClick={() => setSelectedStepId(step.id)}
                    aria-pressed={isSelected}
                  >
                    <span className="dag-node-id">{methodId}</span>
                    <strong className="dag-node-title">{step.title}</strong>
                    {step.description && <span className="dag-node-desc">{step.description}</span>}
                  </button>
                );
              })}
            </div>
          </div>
        </section>
      )}

      <section className="next-steps-section" aria-label="当前步骤下游决策分支">
        <div className="next-steps-head">
          <div>
            <h2>
              当前已完成步骤：{activeStep?.title ?? activeNodeId}
              <span className="badge status-ready">{activeNodeId}</span>
            </h2>
            <p className="small muted">
              以下为依据当前观察现象与中间表契约推荐的下一步分支。点击任意模版的「在代码操控台中打开」即可直接绑列调参并运行。
            </p>
          </div>
          <div className="next-steps-actions">
            <input
              type="search"
              value={branchFilter}
              onChange={(e) => setBranchFilter(e.target.value)}
              placeholder="筛选分支 / 现象 / 模版"
              aria-label="筛选下游分支"
            />
            {activeMethodPage && (
              <>
                <a className="button small" {...pageLink(activeMethodPage.path)}>方法详情</a>
                <a className="button primary small" href={studioHref((activeMethodPage.meta as MethodMeta).id ?? activeNodeId)}>
                  在代码操控台中打开此方法
                </a>
              </>
            )}
          </div>
        </div>

        {loadingNext && <p className="notice" role="status">正在查询 {activeNodeId} 的下游决策分支…</p>}
        {nextError && !filteredBranches.length && (
          <p className="notice">暂未从后端检索到 <code>{activeNodeId}</code> 的结构化 <code>next_steps</code>（{nextError}）。可切换到其他步骤或在方法库查看关联模版。</p>
        )}

        {!loadingNext && filteredBranches.length === 0 && !nextError && (
          <p className="notice">当前步骤 <code>{activeNodeId}</code> 暂无更多下游分支记录（可能已是终端解释/出图阶段）。</p>
        )}

        <div className="branch-grid">
          {filteredBranches.map((branch, idx) => {
            const ifacePage = branch.intermediate_interface
              ? resolvePageById(branch.intermediate_interface, data.pages)
              : undefined;
            const ifaceMeta = ifacePage?.meta.type === 'interface' ? (ifacePage.meta as InterfaceMeta) : undefined;
            return (
              <article key={`${branch.direction}:${idx}`} className="sheet branch-card">
                <div className="branch-card-top">
                  <span className="branch-no">分支 {idx + 1}</span>
                  <h3>{branch.direction}</h3>
                </div>

                <div className="branch-when">
                  <span className="branch-label">触发条件 / 观察现象</span>
                  <p>{branch.when || '完成上一步验证后按研究问题触发'}</p>
                </div>

                {branch.intermediate_interface && (
                  <div className="branch-interface">
                    <span className="branch-label">标准中间表契约</span>
                    <div className="branch-iface-row">
                      {ifacePage ? (
                        <a className="iface-pill" {...pageLink(ifacePage.path)}>
                          <code>{branch.intermediate_interface}.csv</code>
                          <span>{ifacePage.meta.title}</span>
                        </a>
                      ) : (
                        <code className="iface-pill">{branch.intermediate_interface}.csv</code>
                      )}
                      {ifaceMeta && (
                        <span className="small muted">
                          核心列：{Object.keys(ifaceMeta.columns).slice(0, 6).join(', ')}
                          {Object.keys(ifaceMeta.columns).length > 6 ? ' …' : ''}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {branch.analysis_templates.length > 0 && (
                  <div className="branch-templates">
                    <span className="branch-label">推荐分析模版 / 方法</span>
                    <ul className="branch-chip-list">
                      {branch.analysis_templates.map((tid) => {
                        const page = resolvePageById(tid, data.pages);
                        const resolvedId = page && 'id' in page.meta ? page.meta.id : tid.replace(/^(methods|templates|recipes)\//, '').replace(/\.md$/, '');
                        return (
                          <li key={tid} className="branch-template-item">
                            <div className="branch-template-info">
                              {page ? <a {...pageLink(page.path)}>{page.meta.title}</a> : <code>{tid}</code>}
                              <span className="small muted">{resolvedId}</span>
                            </div>
                            <a className="button primary small" href={studioHref(resolvedId)}>
                              在代码操控台中打开
                            </a>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}

                {branch.viz_templates.length > 0 && (
                  <div className="branch-viz">
                    <span className="branch-label">配套可视化模版（含预览）</span>
                    <div className="branch-viz-grid">
                      {branch.viz_templates.map((vid) => {
                        const page = resolvePageById(vid, data.pages);
                        const resolvedId = page && 'id' in page.meta ? page.meta.id : vid.replace(/^(templates|recipes|methods)\//, '').replace(/\.md$/, '');
                        const imgUrl = page ? imageOf(page.meta) : `/files/wiki/templates/${encodeURIComponent(resolvedId)}/preview.png`;
                        return (
                          <div key={vid} className="branch-viz-card">
                            <div className="branch-viz-thumb">
                              {page ? (
                                <FigureImage meta={page.meta} />
                              ) : (
                                <img src={imgUrl ?? undefined} alt={resolvedId} loading="lazy" />
                              )}
                            </div>
                            <div className="branch-viz-meta">
                              <div className="branch-viz-title">
                                {page ? <a {...pageLink(page.path)}>{page.meta.title}</a> : <code>{resolvedId}</code>}
                                {page && 'status' in page.meta && <StatusBadge status={page.meta.status} />}
                              </div>
                              <a className="button primary small" href={studioHref(resolvedId)}>
                                在代码操控台中打开
                              </a>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>

        {!!nextResp?.structural_matches?.length && (
          <details className="method-details">
            <summary>接口结构匹配的其他下游模版 ({nextResp.structural_matches.length})</summary>
            <div className="branch-struct-list">
              {nextResp.structural_matches.map((item) => (
                <div key={item.path || item.id} className="branch-template-item">
                  <div className="branch-template-info">
                    <a {...pageLink(item.path)}>{item.title}</a>
                    <span className="small muted">{item.type} · {item.id}</span>
                  </div>
                  <a className="button small" href={studioHref(item.id)}>在代码操控台中打开</a>
                </div>
              ))}
            </div>
          </details>
        )}
      </section>
    </section>
  );
}
