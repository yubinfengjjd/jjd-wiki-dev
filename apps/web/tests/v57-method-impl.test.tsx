import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { ImplementationStatus, MethodImplementation, MethodMeta, PageSummary } from '../src/api';
import { Flow } from '../src/flow';
import { implPillLabel, MethodImplementations, MethodOverview, sortImplementations } from '../src/views/MethodOverview';
import { MethodsView } from '../src/views/MethodsView';

const graph = { nodes: [], links: [] };
const TAXONOMY = {
  total: 1,
  domains: [{ value: 'single-cell', count: 1, purposes: [{ value: '注释与参考映射', count: 1 }] }],
  data_domains: [{ value: 'single-cell', label: '单细胞转录组', count: 1, purposes: [{ value: '注释与参考映射', count: 1 }] }],
  purposes: [{ value: '注释与参考映射', count: 1 }],
  unclassified: [],
};

const IMPLS: MethodImplementation[] = [
  {
    id: 'scimap-gmm',
    title: 'CyCIF 空间蛋白 GMM 门控注释',
    language: 'Python',
    impl_tier: 'variant',
    modality: 'Spatial Proteomics',
    source_paper: 'Nirmal et al. 2022',
    entrypoint: 'code/scimap_gmm.py:run_gmm_phenotyping',
    dependencies: ['numpy', 'scikit-learn'],
    verification: 'verification/scimap-gmm.json',
  },
  {
    id: 'scp-singler',
    title: 'SCP SingleR 参考注释',
    language: 'R',
    impl_tier: 'default',
    modality: 'scRNA-seq',
    source_paper: 'Aran et al. 2019',
    entrypoint: 'code/singler.R:run_singler',
    dependencies: ['SingleR', 'Seurat'],
    verification: 'verification/scp-singler.json',
  },
];

const STATUSES: ImplementationStatus[] = [
  { id: 'scp-singler', title: 'SCP SingleR 参考注释', state: 'verified', scope: 'PBMC 3k SingleR 实跑断言通过' },
  { id: 'scimap-gmm', title: 'CyCIF 空间蛋白 GMM 门控注释', state: 'verified', scope: 'Melanoma CyCIF 1500-cell GMM 验证通过' },
];

const METHOD_META: MethodMeta = {
  type: 'method',
  id: 'cell-type-annotation',
  title: '细胞类型注释',
  method_kind: 'analysis',
  status: 'ready',
  tags: ['single-cell'],
  data_domains: ['single-cell'],
  purposes: ['注释与参考映射'],
  favorite: false,
  inputs: [],
  outputs: [],
  summary: '跨模态单细胞与空间蛋白细胞类型注释。',
  data_contract: { input: '表达矩阵', output: '细胞类型标签表' },
  implementations: IMPLS,
  source: { kind: 'written' },
  license: 'MIT',
  cite: ['Aran et al. 2019', 'Nirmal et al. 2022'],
};

let failed = 0;
function check(name: string, fn: () => void) {
  try {
    fn();
    console.log(`PASS ${name}`);
  } catch (error: any) {
    failed++;
    console.error(`FAIL ${name}\n${error.stack}`);
  }
}

check('sortImplementations places default first and implPillLabel formats modality + language cleanly', () => {
  const sorted = sortImplementations(IMPLS);
  assert.deepEqual(sorted.map((i) => i.id), ['scp-singler', 'scimap-gmm']);
  assert.equal(implPillLabel(sorted[0], sorted), 'scRNA-seq · R 默认');
  assert.equal(implPillLabel(sorted[1], sorted), 'Spatial Proteomics · Python');

  // Duplicate modality + language disambiguates by id
  const dupPeers: MethodImplementation[] = [
    { ...sorted[0], id: 'impl-a' },
    { ...sorted[0], id: 'impl-b', impl_tier: 'variant' },
  ];
  assert.equal(implPillLabel(dupPeers[0], dupPeers), 'scRNA-seq · R (impl-a) 默认');
  assert.equal(implPillLabel(dupPeers[1], dupPeers), 'scRNA-seq · R (impl-b)');
});

check('HubMethodCard displays verified count, languages, and modality capsules', () => {
  const page: PageSummary<MethodMeta> = {
    path: 'methods/cell-type-annotation.md',
    meta: METHOD_META,
    implementation_status: STATUSES,
  };
  const data = {
    pages: [page],
    graph,
    flow: new Flow(graph),
    taxonomy: TAXONOMY,
    env: { titles: new Map([[page.path, METHOD_META.title]]), hiddenSources: new Set() },
    reload: async () => {},
  } as any;

  const html = renderToStaticMarkup(<MethodsView data={data} query="kind=analysis" />);
  assert.ok(html.includes('2 套已验证实现 · Python / R') || html.includes('2 套已验证实现 · R / Python'));
  assert.ok(html.includes('class="modality-pill">Spatial Proteomics</span>'));
  assert.ok(html.includes('class="modality-pill">scRNA-seq</span>'));
});

check('MethodImplementations renders Apple segmented impl-switcher with active card and full branch details', () => {
  const html = renderToStaticMarkup(
    <MethodImplementations meta={METHOD_META} implementationStatus={STATUSES} />,
  );
  assert.ok(html.includes('class="impl-switcher"'));
  assert.ok(html.includes('可执行实现 (2)'));
  assert.ok(html.includes('scRNA-seq · R 默认'));
  assert.ok(html.includes('Spatial Proteomics · Python'));
  // Active card defaults to impl_tier=default (scp-singler)
  assert.ok(html.includes('class="impl-tier-badge tier-default">主推默认</span>'));
  assert.ok(html.includes('源自 Aran et al. 2019'));
  assert.ok(html.includes('code/singler.R:run_singler'));
  assert.ok(html.includes('SingleR、Seurat'));
  assert.ok(html.includes('PBMC 3k SingleR 实跑断言通过'));
  assert.ok(html.includes('verification/scp-singler.json'));
  // Secondary variant stays accessible in the comparison table
  assert.ok(html.includes('code/scimap_gmm.py:run_gmm_phenotyping'));
  assert.ok(html.includes('Melanoma CyCIF 1500-cell GMM 验证通过'));
  assert.ok(html.includes('场景变体'));
});

check('MethodOverview reflects stale and not_run receipt states accurately', () => {
  const staleMeta: MethodMeta = {
    ...METHOD_META,
    implementations: [
      { ...IMPLS[0], impl_tier: 'default' },
      { ...IMPLS[1], impl_tier: 'variant' },
    ],
  };
  const staleStatuses: ImplementationStatus[] = [
    { id: 'scimap-gmm', title: 'CyCIF', state: 'stale', scope: '源码已改动需重跑 verify-method' },
    { id: 'scp-singler', title: 'SingleR', state: 'not_run', scope: '尚未运行验证脚本' },
  ];
  const html = renderToStaticMarkup(
    <MethodOverview meta={staleMeta} implementationStatus={staleStatuses} figures={[]} pages={[]} />,
  );
  assert.ok(html.includes('class="impl-switcher"'));
  assert.ok(html.includes('验证已过期'));
  assert.ok(html.includes('源码已改动需重跑 verify-method'));
  assert.ok(html.includes('未运行'));
  assert.ok(html.includes('源自 Nirmal et al. 2022'));
});

check('PageView keys MethodOverview by meta.id and App propagates refreshNonce to re-fetch same-page receipts', () => {
  const pageViewSource = readFileSync(resolve(process.cwd(), 'src/views/PageView.tsx'), 'utf8');
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.tsx'), 'utf8');
  assert.match(pageViewSource, /<MethodOverview\s+key=\{meta\.id\}/);
  assert.match(pageViewSource, /<MethodImplementations\s+key=\{meta\.id\}/);
  assert.ok(pageViewSource.includes('[path, data.refreshNonce]'));
  assert.ok(pageViewSource.includes('data.refreshNonce'));
  assert.ok(appSource.includes('refreshNonce'));
  assert.ok(appSource.includes('setRefreshNonce'));
  assert.ok(appSource.includes('pageCache.clear()'));
});

if (failed > 0) process.exit(1);
