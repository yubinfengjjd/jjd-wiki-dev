import { useEffect, useMemo, useState } from 'react';
import {
  api,
  CuratedBranchV2,
  imageOf,
  InterfaceMeta,
  MethodMeta,
  NextStepBranch,
  NextStepsResponse,
  ObjectCandidateV2,
  PageSummary,
  PlaybookItem,
  PlaybookStep,
  studioHref,
} from '../api';
import type { AppData } from '../App';
import { FigureImage, LicenseBadge, StatusBadge } from '../components';
import { pageLink } from '../nav';

const CORE_PLAYBOOK_META: Record<string, { title: string; subtitle: string; steps: PlaybookStep[] }> = {
  'scrna-stepwise-playbook': {
    title: '单细胞转录组步进决策树',
    subtitle: 'QC / 批次整合 → 细胞类型注释 → 七大下游探索分支',
    steps: [
      { id: 'cell-quality-control', title: 'Step 1 · 单细胞质量控制 (QC)', method_id: 'cell-quality-control', description: '线粒体/核糖体/双细胞过滤', next: ['batch-integration'] },
      { id: 'batch-integration', title: 'Step 2 · 批次效应整合与降维聚类', method_id: 'batch-integration', description: 'Harmony / Seurat Anchor / UMAP', next: ['cell-type-annotation'] },
      { id: 'cell-type-annotation', title: 'Step 3 · 细胞类型注释', method_id: 'cell-type-annotation', description: 'Marker 气泡图与参考映射；完成后展开 7 大下游方向', next: ['differential-expression', 'gene-set-scoring', 'trajectory-inference', 'spatial-transcriptomics-microenvironment'] },
      { id: 'differential-expression', title: 'Step 4A · 亚群差异表达 & 富集', method_id: 'differential-expression', description: 'FindMarkers / pseudobulk DEG', next: ['gene-set-enrichment'] },
      { id: 'gene-set-scoring', title: 'Step 4B · 基因集多算法打分', method_id: 'gene-set-scoring', description: 'AUCell / UCell / ssGSEA', next: ['trajectory-inference'] },
      { id: 'trajectory-inference', title: 'Step 4C · 拟时序与动态基因', method_id: 'trajectory-inference', description: 'Monocle2/3 / Slingshot 轨迹分化', next: ['dynamic-feature-analysis', 'rna-velocity'] },
      { id: 'spatial-transcriptomics-microenvironment', title: 'Branch 7 · 单细胞 × 空转微环境子树', method_id: 'spatial-transcriptomics-microenvironment', description: '汇合空转切片，开展 RCTD/签名空间映射、免疫排斥与空间通讯', requires: ['scrna-annotated-cells', 'visium-spatial-object'], subtree: 'scenarios/stromal-tme-scrna-st-playbook', next: [] },
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
  'stromal-tme-scrna-st-playbook': {
    title: '单细胞与空转肿瘤基质微环境思路分支树',
    subtitle: '单细胞基质注释 + Visium 空转双上游汇合 → Ro/e 预后、分化轨迹、空间免疫排斥与 TLS/TAM 通讯',
    steps: [
      { id: 'cell-type-annotation', title: 'Stage 1 · 基质精细亚群注释与跨队列整合', method_id: 'cell-type-annotation', description: 'Fib / EC / Mural 多中心整合与包络边界 UMAP', next: ['cell-proportion-composition', 'spatial-transcriptomics-microenvironment'] },
      { id: 'spatial-transcriptomics-microenvironment', title: 'Stage 2 · 空间去卷积与 H&E 组织分区对齐', method_id: 'spatial-transcriptomics-microenvironment', description: 'RCTD / Spot 空间签名映射与高/低生态位分区', requires: ['scrna-annotated-cells', 'visium-spatial-object'], next: ['cell-proportion-composition', 'immune-infiltration-tme', 'cell-cell-communication'] },
      { id: 'cell-proportion-composition', title: 'Stage 3 · Ro/e 组织偏好与多队列 Cox 预后分层', method_id: 'cell-proportion-composition', description: 'Normal/Tumor/LN 组成比例检验与 TCGA/院内队列预后关联', next: ['gene-set-scoring', 'trajectory-inference'] },
      { id: 'gene-set-scoring', title: 'Stage 4A · 功能基因程序、PROGENy 与 KEGG 代谢刻画', method_id: 'gene-set-scoring', description: '趋化因子/MHC Z-score、通路活性与代谢富集对比', next: ['trajectory-inference', 'immune-infiltration-tme'] },
      { id: 'trajectory-inference', title: 'Stage 4B · DiffusionMap / Slingshot 分化轨迹', method_id: 'trajectory-inference', description: '推断分化起点、双功能模块激活切换与动态基因曲线', next: ['cell-cell-communication'] },
      { id: 'immune-infiltration-tme', title: 'Stage 5 · 基质–免疫排斥相关矩阵与检查点验证', method_id: 'immune-infiltration-tme', description: 'Bulk 免疫共浸润聚类与高/低评分区域检查点表达差异', requires: ['scrna-annotated-cells', 'visium-spatial-object'], next: ['cell-cell-communication'] },
      { id: 'cell-cell-communication', title: 'Stage 6 · TLS / TAM 空间配受体通讯枢纽', method_id: 'cell-cell-communication', description: 'CellChat / CellPhoneDB 互作矩阵、环形信号网与空间共定位验证', requires: ['scrna-annotated-cells', 'visium-spatial-object'], next: [] },
    ],
  },
};

const CORE_PLAYBOOK_ORDER = [
  'scrna-stepwise-playbook',
  'bulk-ml-biomarker-playbook',
  'geneset-theme-playbook',
  'sc-bulk-integration-playbook',
  'stromal-tme-scrna-st-playbook',
];

export interface DataInventoryOption {
  key: string;
  label: string;
  unlocks: string[];
}

export const DATA_INVENTORY_OPTIONS: DataInventoryOption[] = [
  {
    key: 'scrna',
    label: '已注释单细胞数据 (scRNA)',
    unlocks: ['scrna-annotated-cells', 'stromal-subcluster-markers'],
  },
  {
    key: 'st',
    label: 'Visium 空转切片 (ST)',
    unlocks: ['visium-spatial-object'],
  },
  {
    key: 'bulk',
    label: '带随访 Bulk 队列 (TCGA/临床)',
    unlocks: ['bulk-clinical-survival', 'bulk-de-table'],
  },
  {
    key: 'geneset',
    label: '基因集 / 差异基因表',
    unlocks: ['gene-set-list', 'deg-result-table'],
  },
];

export function buildUnlockedSet(selectedKeys: Iterable<string>): Set<string> {
  const selected = new Set(selectedKeys);
  const unlocked = new Set<string>();
  for (const opt of DATA_INVENTORY_OPTIONS) {
    if (selected.has(opt.key)) {
      for (const item of opt.unlocks) unlocked.add(item);
    }
  }
  return unlocked;
}

export function getStepReadiness(
  step: PlaybookStep | undefined,
  unlockedSet: Set<string>,
): { hasRequirements: boolean; reqs: string[]; missingReqs: string[]; ready: boolean } {
  if (!step) return { hasRequirements: false, reqs: [], missingReqs: [], ready: true };
  const reqs = [...new Set([...(step.requires ?? []), ...(step.external_requires ?? [])])];
  if (reqs.length === 0) return { hasRequirements: false, reqs: [], missingReqs: [], ready: true };
  const missingReqs = reqs.filter((r) => !unlockedSet.has(r));
  return {
    hasRequirements: true,
    reqs,
    missingReqs,
    ready: missingReqs.length === 0,
  };
}

interface PositionedNode {
  step: PlaybookStep;
  col: number;
  row: number;
  x: number;
  y: number;
}

const NODE_W = 236;
const NODE_H = 104;
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

export function resolvePlaybookQueryState(query = ''): { playbook: string; step: string; customMethod: string } {
  const params = new URLSearchParams(query.replace(/^\?/, ''));
  const pb = params.get('playbook') || 'scrna-stepwise-playbook';
  const m = params.get('method') || '';
  const s = params.get('step') || '';
  if (m) return { playbook: pb, step: m, customMethod: m };
  if (s) return { playbook: pb, step: s, customMethod: '' };
  return { playbook: pb, step: 'cell-type-annotation', customMethod: '' };
}

export function matchNextResponse(nextResp: NextStepsResponse | null, activeNodeId: string): NextStepsResponse | null {
  if (!nextResp) return null;
  if (nextResp.node_id === activeNodeId || nextResp.requested_id === activeNodeId) return nextResp;
  return null;
}

export function PlaybooksView({ data, query = '' }: { data: AppData; query?: string }) {
  const initial = resolvePlaybookQueryState(query);
  const [serverPlaybooks, setServerPlaybooks] = useState<PlaybookItem[]>([]);
  const [selectedPlaybookId, setSelectedPlaybookId] = useState<string>(initial.playbook);
  const [selectedStepId, setSelectedStepId] = useState<string>(initial.step);
  const [customMethodId, setCustomMethodId] = useState<string>(initial.customMethod);
  const [nextResp, setNextResp] = useState<NextStepsResponse | null>(null);
  const [loadingNext, setLoadingNext] = useState(false);
  const [nextError, setNextError] = useState('');
  const [branchFilter, setBranchFilter] = useState('');
  const [selectedInventory, setSelectedInventory] = useState<string[]>(['scrna']);

  const unlockedSet = useMemo(() => buildUnlockedSet(selectedInventory), [selectedInventory]);
  const toggleInventory = (key: string) => {
    setSelectedInventory((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    );
  };

  useEffect(() => {
    const params = new URLSearchParams(query.replace(/^\?/, ''));
    const m = params.get('method');
    const s = params.get('step');
    const pb = params.get('playbook');
    if (pb) setSelectedPlaybookId(pb);
    if (m) {
      setCustomMethodId(m);
      setSelectedStepId(m);
    } else if (s) {
      setCustomMethodId('');
      setSelectedStepId(s);
    } else {
      setCustomMethodId('');
    }
  }, [query]);

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

  const analysisMethods = useMemo(
    () =>
      data.pages
        .filter((p): p is PageSummary<MethodMeta> => p.meta.type === 'method' && p.meta.method_kind === 'analysis' && p.meta.status !== 'archived')
        .sort((a, b) => a.meta.title.localeCompare(b.meta.title)),
    [data.pages],
  );

  const playbooks = useMemo(() => normalizePlaybooks(serverPlaybooks, data.pages), [serverPlaybooks, data.pages]);
  const activePlaybook = playbooks.find((p) => p.id === selectedPlaybookId) ?? playbooks[0];

  useEffect(() => {
    if (customMethodId) return;
    if (!activePlaybook?.steps.length) return;
    if (!activePlaybook.steps.some((s) => s.id === selectedStepId || s.method_id === selectedStepId)) {
      const preferred = activePlaybook.steps.find((s) => s.id === 'cell-type-annotation') ?? activePlaybook.steps[0];
      setSelectedStepId(preferred.id);
    }
  }, [activePlaybook, selectedStepId, customMethodId]);

  const activeStep = customMethodId ? undefined : (activePlaybook?.steps.find((s) => s.id === selectedStepId) ?? activePlaybook?.steps[0]);
  const activeStepReadiness = useMemo(
    () => getStepReadiness(activeStep, unlockedSet),
    [activeStep, unlockedSet],
  );
  const activeNodeId = customMethodId || activeStep?.method_id || activeStep?.id || selectedStepId;

  useEffect(() => {
    if (!activeNodeId) return;
    if (typeof fetch !== 'function') return;
    let active = true;
    setLoadingNext(true);
    setNextError('');
    api.nextSteps(activeNodeId)
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
  }, [activeNodeId, data.pages]);

  const currentNextResp = matchNextResponse(nextResp, activeNodeId);

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

  const activeMethodPage = resolvePageById(activeNodeId, data.pages);

  // Use v2 curated_branches when returned, or synthesize from currentNextResp.next_steps / method frontmatter for SSR & legacy mocks.
  const curatedBranches: CuratedBranchV2[] = useMemo(() => {
    if (currentNextResp?.curated_branches?.length) return currentNextResp.curated_branches;
    const rawSteps: NextStepBranch[] = currentNextResp?.next_steps?.length
      ? currentNextResp.next_steps
      : activeMethodPage?.meta.type === 'method'
        ? activeMethodPage.meta.next_steps ?? []
        : [];
    return rawSteps.map((s, idx) => ({
      branch_id: s.branch_id || `branch-${idx + 1}`,
      direction: s.direction,
      when: s.when,
      hypothesis: s.hypothesis || s.when || s.direction,
      required_object: s.required_object || '',
      produced_interface: s.intermediate_interface,
      next_methods: s.analysis_templates.map((tid) => {
        const p = resolvePageById(tid, data.pages);
        const clean = p && 'id' in p.meta ? p.meta.id : tid.replace(/^(methods|templates|recipes)\//, '').replace(/\.md$/, '');
        return {
          id: clean,
          title: p?.meta.title ?? clean,
          path: p?.path ?? `methods/${clean}.md`,
          status: p && 'status' in p.meta ? p.meta.status : 'ready',
        };
      }),
      reference_recipes: [],
      viz_templates: s.viz_templates.map((vid) => {
        const p = resolvePageById(vid, data.pages);
        const clean = p && 'id' in p.meta ? p.meta.id : vid.replace(/^(templates|recipes|methods)\//, '').replace(/\.md$/, '');
        return {
          id: clean,
          title: p?.meta.title ?? clean,
          path: p?.path ?? `templates/${clean}.md`,
          status: p && 'status' in p.meta ? p.meta.status : 'ready',
          preview_url: p ? imageOf(p.meta) : null,
        };
      }),
    }));
  }, [currentNextResp, activeMethodPage, data.pages]);

  const filterText = branchFilter.trim().toLowerCase();
  const filteredCurated = filterText
    ? curatedBranches.filter((b) =>
        `${b.direction} ${b.when} ${b.hypothesis} ${b.produced_interface} ${b.next_methods.map((m) => `${m.id} ${m.title}`).join(' ')} ${b.viz_templates.map((v) => `${v.id} ${v.title}`).join(' ')}`
          .toLowerCase()
          .includes(filterText),
      )
    : curatedBranches;

  const objectCandidates: ObjectCandidateV2[] = useMemo(() => {
    const raw = currentNextResp?.object_compatible_candidates ?? [];
    if (!filterText) return raw;
    return raw.filter((c) =>
      `${c.id} ${c.title} ${c.match_type} ${c.shared_interfaces.join(' ')}`.toLowerCase().includes(filterText),
    );
  }, [currentNextResp?.object_compatible_candidates, filterText]);

  const selectMethodNode = (id: string) => {
    const clean = id.replace(/^(methods|templates|recipes)\//, '').replace(/\.md$/, '');
    setCustomMethodId(clean);
    setSelectedStepId(clean);
  };

  return (
    <section className="playbooks-workbench hiplot-playbooks">
      <header className="gallery-top-bar">
        <div className="gallery-title-group">
          <span className="studio-eyebrow">MULTI-BRANCH RESEARCH DECISION SANDBOX</span>
          <h1>多路决策沙盘</h1>
          <p className="muted small">
            科研下游从不是单一线性流程。选择任意分析方法或宏观路线节点，并行查看「精选条件分支」与「基于输出对象推导的兼容候选」，并直接进入出图工作台。
          </p>
        </div>
        <div className="gallery-top-actions">
          <a className="button" href="#/methods">返回分析方法库</a>
          <a className="button primary" href="#/studio">打开作图工作台</a>
        </div>
      </header>

      <div className="playbook-tabs" role="tablist" aria-label="四大生信主线决策树">
        {playbooks.map((pb, idx) => (
          <button
            key={pb.id}
            type="button"
            role="tab"
            aria-selected={!customMethodId && activePlaybook?.id === pb.id}
            className={!customMethodId && activePlaybook?.id === pb.id ? 'playbook-tab active' : 'playbook-tab'}
            onClick={() => {
              setCustomMethodId('');
              setSelectedPlaybookId(pb.id);
            }}
          >
            <span className="playbook-tab-index">主线 {idx + 1}</span>
            <strong>{pb.title}</strong>
            {pb.summary && <small>{pb.summary}</small>}
          </button>
        ))}
      </div>

      {activePlaybook && (
        <section className="sheet dag-panel" aria-label="当前主线分析步骤">
          <div className="dag-header">
            <div>
              <h2>{activePlaybook.title}</h2>
              <p className="small muted">点击主线步骤，或在右侧下拉切换任意分析方法节点，即时查看多路可选下游分支。</p>
            </div>
            <div className="dag-step-select">
              <label className="sandbox-method-picker small">
                <span>任意方法节点：</span>
                <select
                  aria-label="切换任意方法节点"
                  value={activeNodeId}
                  onChange={(e) => selectMethodNode(e.target.value)}
                >
                  {!analysisMethods.some((m) => m.meta.id === activeNodeId) && (
                    <option value={activeNodeId}>{activeNodeId}</option>
                  )}
                  {analysisMethods.map((m) => (
                    <option key={m.meta.id} value={m.meta.id}>
                      {m.meta.title} [{m.meta.id}]
                    </option>
                  ))}
                </select>
              </label>
              {resolvePageById(activePlaybook.path, data.pages) && (
                <a className="button small" {...pageLink(activePlaybook.path)}>路线文档</a>
              )}
            </div>
          </div>

          <div className="data-inventory-bar" role="group" aria-label="我手里有哪些数据">
            <span className="data-inventory-label">我手里有哪些数据？</span>
            <div className="data-inventory-chips">
              {DATA_INVENTORY_OPTIONS.map((opt) => {
                const checked = selectedInventory.includes(opt.key);
                return (
                  <label
                    key={opt.key}
                    className={`inventory-chip${checked ? ' checked' : ''}`}
                    title={`解锁前置条件：${opt.unlocks.join('、')}`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleInventory(opt.key)}
                    />
                    <span>{opt.label}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div className="playbook-step-pills" role="tablist" aria-label="步骤切换">
            {activePlaybook.steps.map((step, sIdx) => {
              const isSelected = !customMethodId && activeStep?.id === step.id;
              return (
                <button
                  key={step.id}
                  type="button"
                  role="tab"
                  aria-selected={isSelected}
                  className={isSelected ? 'step-pill-btn active' : 'step-pill-btn'}
                  onClick={() => {
                    setCustomMethodId('');
                    setSelectedStepId(step.id);
                  }}
                  title={step.description || step.title}
                >
                  <span className="step-pill-num">{sIdx + 1}</span>
                  <span className="step-pill-label">{step.title}</span>
                </button>
              );
            })}
          </div>

          <details className="dag-collapse">
            <summary className="small muted">展开交互式拓扑流程图（{activePlaybook.steps.length} 个步骤节点）</summary>
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
                    const isActive = !customMethodId && (from.step.id === activeStep?.id || to.step.id === activeStep?.id);
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
                  const isSelected = !customMethodId && activeStep?.id === step.id;
                  const isNeighbor = !isSelected && connectedIds.has(step.id);
                  const methodId = step.method_id || step.id;
                  const readiness = getStepReadiness(step, unlockedSet);
                  const readinessClass = readiness.hasRequirements
                    ? (readiness.ready ? ' dag-node-ready' : ' dag-node-locked')
                    : '';
                  return (
                    <button
                      key={step.id}
                      type="button"
                      style={{ left: x, top: y, width: NODE_W, height: NODE_H }}
                      className={`dag-node${isSelected ? ' selected' : ''}${isNeighbor ? ' neighbor' : ''}${readinessClass}`}
                      onClick={() => {
                        setCustomMethodId('');
                        setSelectedStepId(step.id);
                      }}
                      aria-pressed={isSelected}
                    >
                      <span className="dag-node-id">{methodId}</span>
                      <strong className="dag-node-title">{step.title}</strong>
                      {step.description && <span className="dag-node-desc">{step.description}</span>}
                      {(!!step.requires?.length || readiness.hasRequirements) && (
                        <div className="dag-node-pills">
                          {readiness.hasRequirements && (
                            readiness.ready ? (
                              <span className="readiness-pill ready">✓ 数据就绪</span>
                            ) : (
                              <span
                                className="readiness-pill locked"
                                title={`缺少数据：${readiness.missingReqs.join('、')}`}
                              >
                                缺数据: {readiness.missingReqs.join(', ')}
                              </span>
                            )
                          )}
                          {!!step.requires?.length && (
                            <span className="requires-pill" title={`多上游汇合：${step.requires.join(' + ')}`}>
                              多上游汇合: {step.requires.join(' + ')}
                            </span>
                          )}
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          </details>
        </section>
      )}

      <section className="next-steps-section" aria-label="当前节点下游决策分支">
        <div className="next-steps-head">
          <div>
            <h2>
              当前方法节点：{activeMethodPage?.meta.title || activeStep?.title || activeNodeId}{' '}
              <code>{activeNodeId}</code>
            </h2>
            <p className="small muted">
              {currentNextResp?.agent_guidance || '下游分支均为可选科研决策，无固定线性顺序；点击任意推荐方法可继续向下一跳推演，或直接打开模板工作台。'}
            </p>
            <p className="small muted">
              Agent 结构化接口：<code>rwiki next {activeNodeId} --json</code>
            </p>
            {!customMethodId && (activeStepReadiness.hasRequirements || !!activeStep?.requires?.length || !!activeStep?.external_requires?.length) && (
              <div className="step-readiness-row small">
                {activeStepReadiness.hasRequirements && (
                  activeStepReadiness.ready ? (
                    <span className="readiness-pill ready">✓ 数据就绪</span>
                  ) : (
                    <span className="readiness-pill locked">
                      缺数据: {activeStepReadiness.missingReqs.join(', ')}
                    </span>
                  )
                )}
                {!!activeStep?.requires?.length && (
                  <span className="requires-pill">多上游汇合: {activeStep.requires.join(' + ')}</span>
                )}
                {!!activeStep?.external_requires?.length && (
                  <span className="requires-pill">外部数据依赖: {activeStep.external_requires.join(' + ')}</span>
                )}
              </div>
            )}
            {!!activeStep?.subtree && !customMethodId && (() => {
              const targetSubtreeId = activeStep.subtree.split('/').pop()?.replace(/\.md$/, '') ?? '';
              return targetSubtreeId ? (
                <p className="small">
                  <button
                    type="button"
                    className="button primary small"
                    onClick={() => {
                      setCustomMethodId('');
                      setSelectedPlaybookId(targetSubtreeId);
                    }}
                  >
                    进入专题子分支树（{targetSubtreeId}） →
                  </button>
                </p>
              ) : null;
            })()}
          </div>
          <div className="next-steps-actions">
            <input
              type="search"
              value={branchFilter}
              onChange={(e) => setBranchFilter(e.target.value)}
              placeholder="筛选分支 / 假设 / 模版"
              aria-label="筛选下游分支"
            />
            {activeMethodPage && (
              <>
                <a className="button small" {...pageLink(activeMethodPage.path)}>方法工作站详情</a>
                <a className="button primary small" href={studioHref((activeMethodPage.meta as MethodMeta).id ?? activeNodeId)}>
                  在工作台中打开
                </a>
              </>
            )}
          </div>
        </div>

        {loadingNext && <p className="notice" role="status">正在查询 {activeNodeId} 的下游多路分支…</p>}
        {nextError && !filteredCurated.length && !objectCandidates.length && (
          <p className="notice">暂未从后端检索到 <code>{activeNodeId}</code> 的结构化 <code>next_steps</code>（{nextError}）。可在上方切换其他方法节点。</p>
        )}

        <div className="sandbox-split-section">
          <h3>一、精选条件分支 (curated_branches · {filteredCurated.length})</h3>
          {!loadingNext && filteredCurated.length === 0 ? (
            <p className="notice small">当前节点暂无精选条件分支记录；可查看下方基于输出对象自动推导的兼容候选。</p>
          ) : (
            <div className="branch-grid">
              {filteredCurated.map((branch, idx) => {
                const ifacePage = branch.produced_interface
                  ? resolvePageById(branch.produced_interface, data.pages)
                  : undefined;
                const ifaceMeta = ifacePage?.meta.type === 'interface' ? (ifacePage.meta as InterfaceMeta) : undefined;
                return (
                  <article key={`${branch.branch_id}:${idx}`} className="sheet branch-card">
                    <div className="branch-card-top">
                      <span className="branch-no">{branch.branch_id}</span>
                      <h3>{branch.direction}</h3>
                    </div>

                    <div className="branch-when">
                      <span className="branch-label">触发条件 / 研究假设</span>
                      <p>{branch.when || '完成上一步验证后按研究问题触发'}</p>
                      {branch.hypothesis && branch.hypothesis !== branch.when && (
                        <p className="small muted">假设：{branch.hypothesis}</p>
                      )}
                    </div>

                    {(branch.required_object || branch.produced_interface) && (
                      <div className="branch-interface">
                        <span className="branch-label">对象与标准中间表契约</span>
                        <div className="branch-iface-row">
                          {branch.required_object && (
                            <span className="small">需要：<code>{branch.required_object}</code></span>
                          )}
                          {branch.produced_interface && (
                            ifacePage ? (
                              <a className="iface-pill" {...pageLink(ifacePage.path)}>
                                <code>{branch.produced_interface}.csv</code>
                                <span>{ifacePage.meta.title}</span>
                              </a>
                            ) : (
                              <code className="iface-pill">{branch.produced_interface}.csv</code>
                            )
                          )}
                          {ifaceMeta && (
                            <span className="small muted">
                              核心列：{Object.keys(ifaceMeta.columns).slice(0, 5).join(', ')}
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {branch.next_methods.length > 0 && (
                      <div className="branch-templates">
                        <span className="branch-label">推荐下游分析方法</span>
                        <ul className="branch-chip-list">
                          {branch.next_methods.map((m) => (
                            <li key={m.id} className="branch-template-item">
                              <div className="branch-template-info">
                                <a {...pageLink(m.path)}>{m.title}</a>
                                <span className="small muted">{m.id}</span>
                              </div>
                              <div className="branch-item-actions">
                                <button type="button" className="button small" onClick={() => selectMethodNode(m.id)}>
                                  沙盘推演此节点
                                </button>
                                <a className="button primary small" {...pageLink(m.path)}>进入方法</a>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {branch.reference_recipes.length > 0 && (
                      <div className="branch-templates">
                        <span className="branch-label">历史参考模板</span>
                        <ul className="branch-chip-list">
                          {branch.reference_recipes.map((rec) => (
                            <li key={rec.id} className="branch-template-item">
                              <div className="branch-template-info">
                                <a {...pageLink(rec.path)}>{rec.title}</a>
                                <LicenseBadge license={rec.license} />
                              </div>
                              <a className="button small" href={studioHref(rec.id)}>工作台</a>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {branch.viz_templates.length > 0 && (
                      <div className="branch-viz">
                        <span className="branch-label">配套可视化模版（含预览）</span>
                        <div className="branch-viz-grid">
                          {branch.viz_templates.map((v) => {
                            const page = resolvePageById(v.path || v.id, data.pages);
                            const imgUrl = v.preview_url || (page ? imageOf(page.meta) : `/files/wiki/templates/${encodeURIComponent(v.id)}/preview.png`);
                            return (
                              <div key={v.id} className="branch-viz-card">
                                <div className="branch-viz-thumb">
                                  {page ? (
                                    <FigureImage meta={page.meta} />
                                  ) : imgUrl ? (
                                    <img src={imgUrl} alt={v.title} loading="lazy" />
                                  ) : (
                                    <span className="preview-empty">暂无预览</span>
                                  )}
                                </div>
                                <div className="branch-viz-meta">
                                  <div className="branch-viz-title">
                                    {page ? <a {...pageLink(page.path)}>{page.meta.title}</a> : <a {...pageLink(v.path)}>{v.title}</a>}
                                    <StatusBadge status={v.status} label={v.status === 'ready' ? '图模板可用' : undefined} />
                                  </div>
                                  <a className="button primary small" href={studioHref(v.id)}>
                                    打开工作台
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
          )}
        </div>

        <div className="sandbox-split-section">
          <h3>二、基于结果对象推导的兼容候选 (object_compatible_candidates · {objectCandidates.length})</h3>
          <p className="small muted">
            仅根据当前方法输出接口与下游必需/可选输入接口的交集自动推导，不代表科学语义已审查；使用前请核对单位、量纲与前提条件。
          </p>
          {objectCandidates.length > 0 ? (
            <div className="candidate-grid sandbox-candidates">
              {objectCandidates.map((cand) => (
                <article key={`${cand.kind}:${cand.id}`} className="sheet candidate-card">
                  <div className="candidate-card-head">
                    <span className={`match-pill match-${cand.match_type}`}>
                      {cand.match_type === 'full' ? '完整兼容 (full)' : '部分兼容 (partial)'}
                    </span>
                    <span className="badge">{cand.kind === 'method' ? '下游分析方法' : '可视化模板'}</span>
                  </div>
                  <h4><a {...pageLink(cand.path)}>{cand.title}</a></h4>
                  <p className="small muted"><code>{cand.id}</code></p>
                  <p className="small">
                    共享接口：<code>{cand.shared_interfaces.join('、')}</code>
                  </p>
                  {cand.missing_required_interfaces.length > 0 && (
                    <p className="small adaptation-note">
                      缺必需接口：<code>{cand.missing_required_interfaces.join('、')}</code>
                    </p>
                  )}
                  {!!cand.downstream_viz?.length && (
                    <div className="candidate-viz-mini">
                      {cand.downstream_viz.slice(0, 2).map((viz) => (
                        <a key={viz.id} className="viz-mini-pill" {...pageLink(viz.path)}>
                          {viz.preview_url && <img src={viz.preview_url} alt={viz.title} loading="lazy" />}
                          <span>{viz.id}</span>
                        </a>
                      ))}
                    </div>
                  )}
                  <div className="candidate-actions">
                    {cand.kind === 'method' ? (
                      <>
                        <button type="button" className="button small" onClick={() => selectMethodNode(cand.id)}>
                          在沙盘查看下一跳
                        </button>
                        <a className="button primary small" {...pageLink(cand.path)}>进入方法</a>
                      </>
                    ) : (
                      <a className="button primary small" href={studioHref(cand.id)}>打开工作台</a>
                    )}
                  </div>
                </article>
              ))}
            </div>
          ) : currentNextResp?.structural_matches?.length ? (
            <div className="branch-struct-list">
              {currentNextResp.structural_matches.map((item) => (
                <div key={item.path || item.id} className="branch-template-item">
                  <div className="branch-template-info">
                    <a {...pageLink(item.path)}>{item.title}</a>
                    <span className="small muted">{item.type} · {item.id}</span>
                  </div>
                  <a className="button small" href={studioHref(item.id)}>打开工作台</a>
                </div>
              ))}
            </div>
          ) : (
            <p className="small muted">当前节点暂无自动推导的对象兼容下游候选。</p>
          )}
        </div>
      </section>
    </section>
  );
}
