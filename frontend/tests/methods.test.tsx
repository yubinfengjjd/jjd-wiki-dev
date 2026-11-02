import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MethodsView } from '../src/views/MethodsView';
import { MethodOverview } from '../src/views/MethodOverview';
import { PageView } from '../src/views/PageView';
import { Flow } from '../src/flow';
import { api, pageCache } from '../src/api';
import { CodeBranchList } from '../src/CodeViewer';
import { conditionFacts, filterAnalysisMethods, normalizeMethodSelection, packageFacts, parseMethodQuery, purposeOptionsFor } from '../src/methods';
import { parseRoute } from '../src/route';
import { REAL_PAGES } from './real-pages';
import { REAL_DETAILS, REAL_PAGES as REAL_API_PAGES, REAL_TAXONOMY } from './real-taxonomy';

async function main() {
const graph = { nodes: [], links: [] };
const method = (id, kind) => ({ path: `methods/${id}.md`, meta: {
  type: 'method', id, title: id, method_kind: kind, status: 'ready', tags: [], favorite: false,
  summary: `${id} answers its specific research question`, inputs: [], outputs: [],
  source: { kind: 'written' }, license: 'none', cite: [],
}, implementation_status: [] });
const EMPTY_TAXONOMY = { total: 0, domains: [], purposes: [], unclassified: [] };
const dataOf = (pages) => ({ pages, graph, flow: new Flow(graph),
  taxonomy: EMPTY_TAXONOMY,
  env: { titles: new Map(pages.map(p => [p.path, p.meta.title])), hiddenSources: new Set() }, reload: async () => {} });
let failed = 0;
function check(name, fn) {
  try { fn(); console.log(`PASS ${name}`); }
  catch (error) { failed++; console.error(`FAIL ${name}\n${error.stack}`); }
}

// Catches technical/workflow/legacy pages leaking into default analysis recommendations.
const analysis = method('analysis-family', 'analysis');
const workflow = method('workflow-guide', 'workflow');
const technical = method('technical-guide', 'technical');
const unclassified = method('legacy-note', undefined);
const archived = { ...method('archived-family', 'analysis'), meta: { ...analysis.meta, id: 'archived-family', title: 'archived-family', status: 'archived' } };
const pages = [analysis, workflow, technical, unclassified, archived];

check('directory searches technical code and exposes explicit type filters', () => {
  const code = { ...method('local-omics-analysis-guide', 'technical'),
    meta: { ...technical.meta, id: 'local-omics-analysis-guide', title: '组学代码复用',
      keywords: ['DotPlotScores', 'irGSEA'], implementations: [
        { id: 'native-score-dot', title: '原生 DotPlotScores', language: 'R', entrypoint: 'code/native_cases.R:native_score_dot', dependencies: [] },
      ] } };
  const html = renderToStaticMarkup(<MethodsView data={dataOf([...pages, code])} query="q=DotPlotScores" />);
  assert.ok(html.includes('href="#/page/methods/local-omics-analysis-guide.md"'), 'technical code must be searchable');
  assert.ok(html.includes('代码与技术资料') && html.includes('组合流程') && html.includes('分析理论'));
  const only = renderToStaticMarkup(<MethodsView data={dataOf(pages)} query="kind=technical" />);
  assert.ok(only.includes('href="#/page/methods/technical-guide.md"'));
  assert.ok(!only.includes('href="#/page/methods/analysis-family.md"'), 'technical tab must not show analysis cards');
});

check('technical implementation detail shows branch scope without claiming an analysis family', () => {
  const page = { ...method('project-code', 'technical'), backlinks: [], body: '# Project code\n\n## 用途\n\n项目适配。',
    meta: { ...technical.meta, id: 'project-code', title: '项目适配', implementations: [
      { id: 'native-route', title: '依赖原生图', language: 'R', entrypoint: 'code/plot.R:plot', dependencies: ['irGSEA'] },
    ] }, implementation_status: [{ id: 'native-route', state: 'not_run', scope: 'irGSEA package absent' }] };
  pageCache.set(page.path, page);
  const html = renderToStaticMarkup(<PageView path={page.path} data={dataOf([page])} />);
  assert.ok(html.includes('具体实现与验证范围'), 'technical implementations were hidden');
  assert.ok(html.includes('依赖原生图') && html.includes('irGSEA package absent'));
  assert.ok(!html.includes('研究问题与用途'), 'technical page must retain its classification');
});
globalThis.fetch = async () => ({ ok: true, json: async () => pages });
await api.pages();
check('default directory includes typed materials and analysis tab keeps canonical families separate', () => {
  const html = renderToStaticMarkup(<MethodsView data={dataOf(pages)} />);
  for (const id of ['analysis-family','workflow-guide','technical-guide','legacy-note']) {
    assert.ok(html.includes(`href="#/page/methods/${id}.md"`));
  }
  assert.ok(html.includes('待分类'));
  assert.ok(!html.includes('archived-family'));
  const canonical = renderToStaticMarkup(<MethodsView data={dataOf(pages)} query="kind=analysis" />);
  assert.ok(canonical.includes('href="#/page/methods/analysis-family.md"'));
  for (const id of ['workflow-guide','technical-guide','legacy-note']) assert.ok(!canonical.includes(`href="#/page/methods/${id}.md"`));
  assert.ok(canonical.includes('暂无已验证实现'));
  assert.ok(!canonical.includes('>可用<'));
});

const detailed = {
  ...method('single-canonical-method', 'analysis'),
  meta: { ...analysis.meta, id: 'single-canonical-method', title: 'single-canonical-method',
    data_contract: { input: '已拟合模型、固定背景与解释样本', output: '带方向的逐样本贡献表' },
    implementations: [
      { id: 'tree', title: 'Tree branch', language: 'Python', entrypoint: 'code/explain.py:explain_tree', dependencies: ['shap'], verification: 'verification/tree.json' },
      { id: 'linear', title: 'Linear branch', language: 'Python', entrypoint: 'code/explain.py:explain_linear', dependencies: ['shap', 'numpy'], verification: 'verification/linear.json' },
      { id: 'changed', title: 'Changed branch', language: 'R', entrypoint: 'code/changed.R:run', dependencies: [], verification: 'verification/changed.json' },
      { id: 'bad', title: 'Invalid branch', language: 'R', entrypoint: 'code/bad.R:run', dependencies: [], verification: 'verification/bad.json' },
    ],
  },
  implementation_status: [
    { id: 'tree', title: 'Tree branch', state: 'verified', scope: '固定树模型加法性断言' },
    { id: 'linear', title: 'Linear branch', state: 'not_run', scope: '依赖未满足，未执行' },
    { id: 'changed', title: 'Changed branch', state: 'stale', scope: '源码已变更' },
    { id: 'bad', title: 'Invalid branch', state: 'invalid', scope: '收据无效' },
  ],
  body: '# single-canonical-method\n\n<!-- facts:start -->\n- generated history fact\n<!-- facts:end -->\n\n## 用途\n\nCanonical purpose only once.\n\nSecond purpose paragraph preserves uncertainty.\n\n## 输入\n\nBody input detail must not duplicate the data contract.\n\n## 输出\n\nBody output detail must not duplicate the data contract.\n\n## 适用\n\nOnly fixed background data.\n\n## 不适用\n\nNo causal conclusion.\n\n## 参数\n\nSampling parameter evidence.\n\n## 代码\n\n```python\n## source heading inside code must survive\nrun()\n```\n\n## 来源与历史\n\nOriginal scientific provenance.\n\n## 知识关联检查\n\nRelationship evidence remains accessible.\n\n<!-- user:start -->\nAuthor note preserved.\n<!-- user:end -->\n',
  backlinks: [], gallery: null, relations: [],
};
pageCache.set(detailed.path, detailed);
const detailData = dataOf([detailed]);
check('method detail renders canonical purpose and scientific conditions once with folded evidence', () => {
  const html = renderToStaticMarkup(<PageView path={detailed.path} data={detailData} />);
  assert.equal((html.match(/<h1>/g) || []).length, 1);
  assert.equal((html.match(/Canonical purpose only once\./g) || []).length, 1);
  for (const text of ['Second purpose paragraph preserves uncertainty.', 'Only fixed background data.', 'No causal conclusion.',
    'Original scientific provenance.', 'Sampling parameter evidence.', '## source heading inside code must survive', 'Relationship evidence remains accessible.', 'Author note preserved.', 'generated history fact']) {
    assert.ok(html.includes(text), text);
  }
  for (const text of ['Sampling parameter evidence.', 'Original scientific provenance.', 'Relationship evidence remains accessible.']) {
    assert.match(html, new RegExp('<details[^>]*>[\\s\\S]*?' + text.replaceAll('.', '\\.') + '[\\s\\S]*?</details>'));
  }
  assert.ok(html.includes('已拟合模型、固定背景与解释样本'));
  assert.ok(html.includes('带方向的逐样本贡献表'));
  assert.ok(html.indexOf('Canonical purpose only once.') < html.indexOf('输入对象'));
  assert.ok(html.indexOf('Canonical purpose only once.') < html.indexOf('具体实现与验证范围'));
  assert.ok(html.includes('<h2>研究问题与用途</h2>'));
  assert.ok(!html.includes('Body input detail must not duplicate'));
  assert.ok(!html.includes('Body output detail must not duplicate'));
  assert.equal((html.match(/已拟合模型、固定背景与解释样本/g) || []).length, 1);
});
check('each implementation displays its own verification scope and executable contract', () => {
  const html = renderToStaticMarkup(<PageView path={detailed.path} data={detailData} />);
  for (const text of ['code/explain.py:explain_tree', 'code/explain.py:explain_linear', 'shap', 'numpy',
    '固定树模型加法性断言', '依赖未满足，未执行', '已验证', '未运行', '验证已过期', '验证无效']) assert.ok(html.includes(text), text);
  assert.ok(!html.includes('>可用<'), 'knowledge confirmation cannot imply all algorithms are executable');
});
check('missing derived implementation status is never inferred from a receipt path', () => {
  const unverified = { ...detailed, path: 'methods/missing-status.md', implementation_status: undefined };
  pageCache.set(unverified.path, unverified);
  const html = renderToStaticMarkup(<PageView path={unverified.path} data={dataOf([unverified])} />);
  assert.ok(html.includes('未运行'));
  assert.ok(!html.includes('>已验证<'));
});
check('technical and workflow details skip analysis overviews and keep their body purpose', () => {
  const technicalPage = {
    ...method('technical-source', 'technical'),
    meta: { ...method('technical-source', 'technical').meta, summary: 'Source material.' },
    body: '# technical-source\n\n## 用途\n\nTechnical purpose appears once.\n\n## 输入\n\nSource files and provenance.\n\n<!-- user:start -->\n<!-- user:end -->\n',
    backlinks: [], gallery: null, relations: [],
  };
  pageCache.set(technicalPage.path, technicalPage);
  const html = renderToStaticMarkup(<PageView path={technicalPage.path} data={dataOf([technicalPage])} />);
  assert.equal((html.match(/Technical purpose appears once/g) || []).length, 1);
  assert.ok(!html.includes('具体实现与验证范围'));
  assert.ok(!html.includes('可以怎样画'));
  assert.ok(!html.includes('研究问题与用途'));
  assert.ok(html.includes('Source files and provenance'));
});
check('real analysis family puts purpose first and prints its data contract once', () => {
  const page = REAL_PAGES.find((p) => p.path === 'methods/cell-quality-control.md')!;
  pageCache.set(page.path, page);
  const html = renderToStaticMarkup(<PageView path={page.path} data={dataOf([page])} />);
  const purpose = '在进入归一化、整合、降维之前';
  assert.equal((html.match(new RegExp(purpose, 'g')) || []).length, 1);
  assert.ok(html.indexOf(purpose) < html.indexOf('输入对象'));
  assert.ok(html.indexOf(purpose) < html.indexOf('具体实现与验证范围'));
  assert.equal((html.match(/Seurat RNA assay 的原始 counts/g) || []).length, 1);
  assert.ok(html.includes('SCP RunCellQC 封装') && html.includes('已验证'));
});
check('real technical/workflow labels use method_kind in breadcrumbs and backlinks', () => {
  const data = dataOf(REAL_PAGES);
  const technical = REAL_PAGES.find((p) => p.path === 'methods/scp-cellqc-doublet.md')!;
  const workflow = REAL_PAGES.find((p) => p.path === 'methods/scp-standard-workflow.md')!;
  const analysis = REAL_PAGES.find((p) => p.path === 'methods/cell-quality-control.md')!;
  for (const [page, label] of [[technical, '技术资料'], [workflow, '组合流程']] as const) {
    pageCache.set(page.path, page);
    const html = renderToStaticMarkup(<PageView path={page.path} data={data} />);
    assert.ok(html.includes(`/ ${label}`), `${page.path} breadcrumb ${label}`);
    assert.ok(!html.includes('/ 分析方法'), `${page.path} is not an analysis method`);
  }
  pageCache.set(analysis.path, analysis);
  const html = renderToStaticMarkup(<PageView path={analysis.path} data={data} />);
  assert.ok(html.includes('title="技术资料"'));
  assert.ok(html.includes('title="组合流程"'));
  assert.ok(!html.includes('title="分析方法"'));
});
check('real technical source page has no analysis overview or empty figure block', () => {
  const page = REAL_PAGES.find((p) => p.path === 'methods/scp-cellqc-doublet.md')!;
  pageCache.set(page.path, page);
  const html = renderToStaticMarkup(<PageView path={page.path} data={dataOf([page])} />);
  assert.ok(html.includes('资料类型：技术/来源资料'));
  assert.ok(!html.includes('具体实现与验证范围'));
  assert.ok(!html.includes('可以怎样画'));
  assert.ok(!html.includes('研究问题与用途'));
  assert.equal((html.match(/用 SCP 的/g) || []).length, 1);
});
check('real multi-branch family keeps branch scopes independent', () => {
  const page = REAL_PAGES.find((p) => p.path === 'methods/batch-integration.md')!;
  pageCache.set(page.path, page);
  const html = renderToStaticMarkup(<PageView path={page.path} data={dataOf([page])} />);
  for (const text of ['SCP Seurat_integrate 锚点分支', 'SCP Harmony_integrate 分支', '已验证', '未运行']) {
    assert.ok(html.includes(text), text);
  }
});
check('shared code file lists every branch and does not merge their scope', () => {
  const html = renderToStaticMarkup(<CodeBranchList branches={[
    { id: 'first', title: 'First branch', state: 'verified', scope: 'First scope only', receipt: 'verification/first.json',
      runtime: { mode: 'standalone', declared: true, files: ['code/first.py'], resources: [],
        required_packages: { Python: ['numpy'] }, optional_packages: {},
        portability: { state: 'verified', scope: 'isolated copy', evidence: 'verification/portability.json', closure_hash: 'x' } } } as any,
    { id: 'other', title: 'Other branch', state: 'not_run', scope: 'Other scope not run', receipt: '',
      runtime: { mode: 'standalone', declared: true, files: ['code/other.R'], resources: [],
        required_packages: { R: ['Seurat'] }, optional_packages: {},
        portability: { state: 'declared', scope: '', evidence: null, closure_hash: null } } } as any,
  ]} />);
  assert.ok(html.includes('First branch') && html.includes('Other branch'));
  assert.ok(html.includes('First scope only') && html.includes('Other scope not run'));
  assert.ok(html.includes('已验证') && html.includes('未运行'));
  assert.ok(html.includes('独立模块') && html.includes('独立迁移已验证'));
  assert.ok(html.includes('独立声明，尚未验证'), 'declaration is not shown as verified');
  assert.ok(html.includes('必要依赖：Python: numpy') && html.includes('必要依赖：R: Seurat'));
});
check('mixed-language dependencies keep their language ownership', () => {
  const text = packageFacts({ required_packages: { R: ['Seurat'], Python: ['scanpy', 'numpy'] } } as any);
  assert.equal(text, 'R: Seurat；Python: scanpy、numpy');
});
// --- Research domain -> analysis purpose: one page, multiple discoverable entries, distinct counts ---
const taxonomy = {
  total: 3,
  domains: [
    { value: '单细胞分析', count: 3, purposes: [
      { value: '降维与聚类', count: 2 }, { value: '模型评价', count: 2 }] },
    { value: '转录组', count: 1, purposes: [{ value: '降维与聚类', count: 1 }] },
  ],
  purposes: [{ value: '降维与聚类', count: 2 }, { value: '模型评价', count: 2 }],
  unclassified: [],
};
const taxMethod = (id, tags, purposes) => ({ ...method(id, 'analysis'),
  meta: { ...method(id, 'analysis').meta, tags, purposes } });
const taxPages = [
  taxMethod('qc-umap', ['单细胞分析', '转录组'], ['降维与聚类']),
  taxMethod('reg-eval', ['单细胞分析'], ['模型评价']),
  taxMethod('both', ['单细胞分析'], ['降维与聚类', '模型评价']),
  method('flow-note', 'workflow'),
];
const taxData = (query = '') => ({ ...dataOf(taxPages), taxonomy });
check('domain and purpose navigation use backend vocabulary and distinct counts', () => {
  const html = renderToStaticMarkup(<MethodsView data={taxData()} query="kind=analysis" />);
  assert.ok(html.includes('全部 3'));
  assert.ok(html.includes('单细胞分析 3'));
  assert.ok(html.includes('转录组 1'));
  assert.ok(html.includes('降维与聚类 2'));
  assert.ok(html.includes('模型评价 2'));
  assert.ok(html.includes('href="#/methods?domain=%E5%8D%95%E7%BB%86%E8%83%9E%E5%88%86%E6%9E%90&amp;kind=analysis"'));
});
check('one page appears once even with multiple domain and purpose memberships', () => {
  const html = renderToStaticMarkup(<MethodsView data={taxData()} query="" />);
  const fronts = (id) => (html.match(new RegExp(`class="face front" href="#/page/methods/${id}\\.md"`, 'g')) || []).length;
  assert.equal(fronts('both'), 1);
  assert.equal(fronts('qc-umap'), 1);
});
check('domain and purpose selection is an intersection and keeps the same canonical page', () => {
  const html = renderToStaticMarkup(<MethodsView data={taxData()} query="?domain=%E5%8D%95%E7%BB%86%E8%83%9E%E5%88%86%E6%9E%90&purpose=%E6%A8%A1%E5%9E%8B%E8%AF%84%E4%BB%B7" />);
  const main = html.slice(0, html.indexOf('<summary>辅助资料'));
  assert.ok(main.includes('href="#/page/methods/reg-eval.md"'));
  assert.ok(main.includes('href="#/page/methods/both.md"'));
  assert.ok(!main.includes('href="#/page/methods/qc-umap.md"'));
  assert.ok(!main.includes('href="#/page/methods/flow-note.md"'));
});
check('switching to a domain resets a purpose that has no content there', () => {
  const html = renderToStaticMarkup(<MethodsView data={taxData()} query="?domain=%E8%BD%AC%E5%BD%95%E7%BB%84&purpose=%E6%A8%A1%E5%9E%8B%E8%AF%84%E4%BB%B7" />);
  assert.ok(html.includes('href="#/page/methods/qc-umap.md"'));
  assert.ok(!html.includes('href="#/page/methods/reg-eval.md"'));
  const normalized = normalizeMethodSelection(parseMethodQuery('?domain=转录组&purpose=模型评价'), taxonomy);
  assert.equal(normalized.purpose, '');
  assert.deepEqual(purposeOptionsFor(taxonomy, '转录组').map(item => item.value), ['降维与聚类']);
});
check('search and empty results stay explicit with a return-to-all link', () => {
  const matched = renderToStaticMarkup(<MethodsView data={taxData()} query="?q=reg-eval" />);
  assert.ok(matched.includes('href="#/page/methods/reg-eval.md"'));
  assert.ok(!matched.includes('href="#/page/methods/both.md"'));
  const empty = renderToStaticMarkup(<MethodsView data={taxData()} query="?q=no-such-method" />);
  assert.ok(empty.includes('没有匹配的方法'));
  assert.ok(empty.includes('href="#/methods?kind=all"'));
});
check('technical and workflow material stays out of analysis filtering', () => {
  const paths = filterAnalysisMethods(taxPages, taxonomy, { domain: '', purpose: '', q: '' }).map(p => p.path);
  assert.deepEqual(paths, ['methods/qc-umap.md', 'methods/reg-eval.md', 'methods/both.md']);
  const html = renderToStaticMarkup(<MethodsView data={taxData()} query="" />);
  const auxiliaryAt = html.indexOf('class="method-auxiliary"');
  assert.ok(auxiliaryAt > 0);
  assert.ok(html.slice(auxiliaryAt).includes('href="#/page/methods/flow-note.md"'));
});
check('the 22 interface schemas are folded behind a reachable entry', () => {
  const interfaces = Array.from({ length: 22 }, (_, i) => ({
    path: `interfaces/i${i}.md`,
    meta: { type: 'interface', slug: `i${i}`, title: `接口 ${i}`, columns: { value: { type: 'float', description: '值' } } },
  }));
  const data = { ...dataOf([...taxPages, ...interfaces]), taxonomy } as any;
  const html = renderToStaticMarkup(<MethodsView data={data} query="kind=analysis" />);
  const summaryAt = html.indexOf('<summary>数据接口');
  assert.ok(summaryAt > 0, 'interface section is folded');
  assert.ok(html.indexOf('接口 0') > summaryAt, 'interface detail remains reachable inside the fold');
  assert.ok(html.indexOf('class="chip"') === -1 || html.indexOf('class="chip"') > summaryAt);
});
check('method overview shows semantic input first and folds required/optional internal columns', () => {
  const interfaces = [
    { path: 'interfaces/render-dotplot-long.md', meta: { type: 'interface', slug: 'render-dotplot-long', title: '点图表',
      columns: {
        group: { type: 'str', description: '分组', required: true },
        feature: { type: 'str', description: '基因', required: true },
        avg_expression: { type: 'float', description: '平均表达', required: true },
        pct_expressed: { type: 'float', description: '阳性比例 0–100', required: true },
        target_group: { type: 'str', description: '目标组', required: false },
      } } },
  ];
  const page = { ...method('with-inputs', 'analysis'),
    meta: { ...method('with-inputs', 'analysis').meta, outputs: ['render-dotplot-long'],
      data_contract: { input: '组级汇总的细胞类型与基因', output: '一张点图表' } },
    body: '# with-inputs\n\n## 用途\n\nA bounded purpose.\n\n<!-- user:start -->\n<!-- user:end -->\n',
    backlinks: [], gallery: null, relations: [], implementation_status: [] };
  pageCache.set(page.path, page);
  const html = renderToStaticMarkup(<PageView path={page.path} data={dataOf([page, ...interfaces])} />);
  assert.ok(html.includes('组级汇总的细胞类型与基因'));
  assert.ok(html.includes('内部表格式'));
  assert.ok(html.includes('可选'));
  assert.ok(html.includes('target_group'));
  assert.ok(html.includes('--bindings'));
  assert.ok(html.indexOf('组级汇总的细胞类型与基因') < html.indexOf('内部表格式'));
});
check('template detail exposes the internal binding contract without claiming unit validation', () => {
  const page = { ...method('template-contract', 'analysis'),
    meta: { type: 'template', id: 'template-contract', title: '模板', status: 'ready', tags: [], favorite: false,
      language: 'r', layouts: ['x'], panels: ['A'], chart_types: ['dotplot'] },
    body: '# 模板\n\n## 适用\n\n说明\n\n<!-- user:start -->\n<!-- user:end -->\n',
    backlinks: [], gallery: null, relations: [], implementation_status: [],
    input_contract: { bindings: true, tables: [{ key: 'dotplot', interface: 'render-dotplot-long',
      description: '点图', required: true, columns: [
        { name: 'group', type: 'str', description: '分组', required: true },
        { name: 'target_group', type: 'str', description: '目标组', required: false }] }] } };
  pageCache.set(page.path, page);
  const html = renderToStaticMarkup(<PageView path={page.path} data={dataOf([page])} />);
  assert.ok(html.includes('数据输入与绑定'));
  assert.ok(html.includes('render-dotplot-long'));
  assert.ok(html.includes('必需') && html.includes('可选'));
  assert.ok(html.includes('--bindings'));
  assert.ok(html.includes('不验证单位'));
});
check('hash route keeps query out of the view and does not decode it as a path', () => {
  const route = parseRoute('#/methods?domain=%E5%8D%95%E7%BB%86%E8%83%9E%E5%88%86%E6%9E%90&q=a%26b');
  assert.equal(route.view, 'methods');
  assert.equal(route.arg, '');
  assert.equal(route.query, 'domain=%E5%8D%95%E7%BB%86%E8%83%9E%E5%88%86%E6%9E%90&q=a%26b');
  const parsed = parseMethodQuery(route.query);
  assert.equal(parsed.domain, '单细胞分析');
  assert.equal(parsed.q, 'a&b');
  const page = parseRoute('#/page/methods/2026-x.md?x=1');
  assert.equal(page.view, 'page');
  assert.equal(page.arg, 'methods/2026-x.md');
  assert.equal(page.query, 'x=1');
  assert.equal(parseRoute('#/methods').view, 'methods');
  assert.equal(parseRoute('#/gallery').view, 'gallery');
});
check('search matches purposes and is controlled by the URL query', () => {
  const data = { ...dataOf(REAL_API_PAGES), taxonomy: REAL_TAXONOMY } as any;
  const html = renderToStaticMarkup(<MethodsView data={data} query="?q=%E6%A8%A1%E5%9E%8B%E8%A7%A3%E9%87%8A" />);
  assert.ok(html.includes('href="#/page/methods/shap-explanation.md"'));
  assert.ok(!html.includes('href="#/page/methods/trajectory-inference.md"'));
  assert.match(html, /<input[^>]*value="模型解释"/);
  const cleared = renderToStaticMarkup(<MethodsView data={data} query="" />);
  assert.match(cleared, /<input[^>]*value=""/);
});
check('real API taxonomy drives SSR without a second word list or duplicate cards', () => {
  const data = { ...dataOf(REAL_API_PAGES), taxonomy: REAL_TAXONOMY } as any;
  const html = renderToStaticMarkup(<MethodsView data={data} query="kind=analysis" />);
  assert.ok(html.includes('全部 15'));
  assert.ok(html.includes('单细胞分析 13'));
  assert.ok(html.includes('转录组 4'));
  assert.ok(html.includes('轨迹与动态分析 3'));
  const fronts = (id) => (html.match(new RegExp(`class="face front" href="#/page/methods/${id}\\.md"`, 'g')) || []).length;
  assert.equal(fronts('gene-set-scoring'), 1, 'a page with two domain tags is one card');
  const filtered = renderToStaticMarkup(<MethodsView data={data} query="?domain=%E5%8D%95%E7%BB%86%E8%83%9E%E5%88%86%E6%9E%90&purpose=%E8%BD%A8%E8%BF%B9%E4%B8%8E%E5%8A%A8%E6%80%81%E5%88%86%E6%9E%90" />);
  for (const id of ['trajectory-inference', 'rna-velocity', 'dynamic-feature-analysis']) {
    assert.ok(filtered.includes(`href="#/page/methods/${id}.md"`), id);
  }
  assert.ok(!filtered.includes('href="#/page/methods/shap-explanation.md"'));
  assert.ok(!filtered.includes('href="#/page/methods/gene-set-scoring.md"'));
});
check('real method detail keeps semantic input first and folds the internal schema', () => {
  const detail = REAL_DETAILS.find((page) => page.path === 'methods/shap-explanation.md')!;
  const pages = REAL_API_PAGES.map((page) => page.path === detail.path ? detail : page);
  pageCache.set(detail.path, detail);
  const html = renderToStaticMarkup(<PageView path={detail.path} data={dataOf(pages)} />);
  const semantic = '已拟合模型、背景 DataFrame、解释样本 DataFrame';
  assert.equal((html.match(new RegExp(semantic, 'g')) || []).length, 1);
  assert.ok(html.indexOf(semantic) < html.indexOf('内部表格式'));
  assert.ok(html.includes('内部表格式'));
  for (const text of ['shap-summary', 'feature', 'percent', '--bindings', '不验证单位']) assert.ok(html.includes(text), text);
  assert.match(html, /<details[^>]*class="method-details method-input-contract"[\s\S]*?percent[\s\S]*?<\/details>/);
});
check('real template detail exposes required/optional internal binding contract', () => {
  for (const [path, optional] of [
    ['templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md', 'target_group'],
    ['templates/2026-10-22-scp-example__fig09-bar--bar.md', 'cell'],
  ] as const) {
    const detail = REAL_DETAILS.find((page) => page.path === path)!;
    pageCache.set(detail.path, detail);
    const html = renderToStaticMarkup(<PageView path={detail.path} data={dataOf([detail])} />);
    assert.ok(html.includes('数据输入与绑定'), path);
    assert.ok(html.includes('render-'), path);
    assert.ok(html.includes(optional), `${path} ${optional}`);
    assert.ok(html.includes('必需') && html.includes('可选'), path);
    assert.ok(html.includes('--bindings'), path);
    assert.ok(html.includes('不验证单位'), path);
    assert.ok(!html.includes('unit validated'), path);
  }
});
check('template runtime issues stay visible without blocking the page', () => {
  const base = REAL_DETAILS.find((page) => page.path.startsWith('templates/'))!;
  const detail = {
    ...base,
    runtime: {
      mode: 'unknown', declared: false, files: [], resources: [],
      required_packages: {}, optional_packages: {},
      portability: { state: 'unknown', scope: '', evidence: null, closure_hash: null,
        issues: ['resources 必须为列表'] },
    },
  };
  pageCache.set(detail.path, detail);
  const html = renderToStaticMarkup(<PageView path={detail.path} data={dataOf([detail])} />);
  assert.ok(html.includes('清单问题：resources 必须为列表'));
});
check('conditional tool and hardware requirements display their conditions', () => {
  const runtime = {
    mode: 'standalone', declared: true, files: [], resources: [],
    required_packages: {}, optional_packages: {},
    portability: { state: 'declared', scope: '', evidence: null, closure_hash: null },
    tools: [{ name: 'vina', condition: 'docking_only' }],
    hardware: { accelerator: 'gpu', condition: 'training_only' },
  } as any;
  const facts = conditionFacts(runtime).join('；');
  assert.ok(facts.includes('docking_only'), `tool condition hidden: ${facts}`);
  assert.ok(facts.includes('training_only'), `hardware condition hidden: ${facts}`);
  const unconditional = { ...runtime,
    tools: [{ name: 'vina' }], hardware: { accelerator: 'gpu' } };
  assert.ok(!conditionFacts(unconditional).join('').includes('条件'),
    'old manifests without conditions must not gain a qualifier');
  // Analysis methods show per-branch runtimes from implementation_status.
  const analysis = { ...method('conditional-runtime', 'analysis'),
    meta: { ...method('conditional-runtime', 'analysis').meta,
      implementations: [{ id: 'dock', title: 'Docking branch', language: 'CLI',
        entrypoint: 'vina', dependencies: [] }] },
    implementation_status: [{ id: 'dock', title: 'Docking branch', state: 'not_run',
      scope: 'declared only', runtime }],
    body: '# conditional-runtime\n\n## 用途\n\nA bounded purpose.\n\n<!-- user:start -->\n<!-- user:end -->\n',
    backlinks: [], gallery: null, relations: [] };
  pageCache.set(analysis.path, analysis);
  const html = renderToStaticMarkup(<PageView path={analysis.path} data={dataOf([analysis])} />);
  assert.ok(html.includes('docking_only'), 'method view hides the tool condition');
  assert.ok(html.includes('training_only'), 'method view hides the hardware condition');
  // Template pages show the page-level runtime block.
  const template = { ...method('conditional-template', 'analysis'),
    meta: { type: 'template', id: 'conditional-template', title: '条件模板',
      status: 'ready', tags: [], favorite: false, language: 'cli',
      layouts: ['x'], panels: ['A'], chart_types: ['bar'] },
    runtime,
    body: '# 模板\n\n## 适用\n\n说明\n\n<!-- user:start -->\n<!-- user:end -->\n',
    backlinks: [], gallery: null, relations: [], implementation_status: [] };
  pageCache.set(template.path, template);
  const html2 = renderToStaticMarkup(<PageView path={template.path} data={dataOf([template])} />);
  assert.ok(html2.includes('docking_only'), 'template view hides the tool condition');
  assert.ok(html2.includes('training_only'), 'template view hides the hardware condition');
});
check('method figure card qualifies template availability, never analysis readiness', () => {
  const figure = { path: 'templates/ridge-fig.md',
    meta: { type: 'template', id: 'ridge-fig', title: 'ridge', status: 'ready',
      tags: [], favorite: false, language: 'r', layouts: [], panels: ['A'],
      chart_types: ['ridge'] },
    relation: 'semantic',
    semantic: { method: 'methods/card-method.md', figure: 'templates/ridge-fig.md',
      method_title: 'card-method', figure_title: 'ridge', method_status: 'ready',
      figure_status: 'ready', compatibility: 'adaptable',
      reason: '输出列契约兼容', prerequisites: [], adaptation: '绑定列名',
      evidence: [], verification: { state: 'verified' },
      target_kind: 'template', active: true } };
  const html = renderToStaticMarkup(<MethodOverview meta={method('card-method', 'analysis').meta}
    figures={[figure]} pages={[]} hiddenSources={new Set()} />);
  assert.ok(html.includes('图模板可用'), 'template availability must carry its noun');
  assert.ok(html.includes('需要适配'), 'adaptation state preserved');
  assert.ok(!html.includes('>可用<'), 'bare availability could read as analysis ready');
});
check('method LIST card figure stack qualifies template availability separately', () => {
  // The reported ambiguity lived in the MethodsView card's .chain-ref-label,
  // not the detail card: a ready associated template next to '需要适配' must
  // not read as the unverified analysis being available.
  const listMethod = { ...method('unverified-m', 'analysis'),
    relations: [{ method: 'methods/unverified-m.md', figure: 'templates/ridge-fig.md',
      method_title: 'unverified-m', figure_title: 'ridge', method_status: 'ready',
      figure_status: 'ready', compatibility: 'adaptable', reason: '输出列契约兼容',
      prerequisites: [], adaptation: '绑定列名', evidence: [],
      verification: { state: 'not_run' }, target_kind: 'template', active: true }] };
  const ridgeTemplate = { path: 'templates/ridge-fig.md', meta: {
    type: 'template', id: 'ridge-fig', title: 'ridge', status: 'ready',
    tags: [], favorite: false, language: 'r', layouts: [], panels: ['A'],
    chart_types: ['ridge'] } };
  const html = renderToStaticMarkup(<MethodsView data={dataOf([listMethod, ridgeTemplate])} />);
  assert.ok(html.includes('需要适配 · 图模板可用'),
    'list card must qualify availability as the figure template');
  assert.ok(!html.includes('· 可用<'), 'bare availability reads as analysis ready');
  assert.ok(html.includes('暂无已验证实现'), 'unverified analysis state preserved');
});
if (failed) process.exitCode = 1;
}
main().catch(error => { console.error(error); process.exitCode = 1; });
