import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import type { PageSummary } from '../src/api';
import { buildSpotlightItems, filterSpotlightItems, SpotlightPalette } from '../src/SpotlightPalette';

const mockPages: PageSummary[] = [
  {
    path: 'templates/tri-panel-stage-umap.md',
    meta: {
      type: 'template',
      id: 'tri-panel-stage-umap',
      title: '三联演进分期 UMAP',
      status: 'ready',
      tags: ['spatial', 'umap'],
      favorite: false,
      language: 'python',
      panels: ['2A'],
      chart_types: ['umap'],
      primary_method: 'cell-type-annotation',
      style_tier: 'variant',
      journal_style: 'Cancer Discovery',
    },
    figure_refs: [],
  },
  {
    path: 'methods/cell-type-annotation.md',
    meta: {
      type: 'method',
      id: 'cell-type-annotation',
      title: '细胞类型注释',
      status: 'ready',
      method_kind: 'analysis',
      tags: ['single-cell'],
      favorite: false,
      inputs: [],
      outputs: [],
      source: { kind: 'written' },
      license: 'MIT',
      cite: [],
      summary: '基于经典标志基因与参考图谱对单细胞/空间细胞进行表型注释',
    },
    figure_refs: [],
  },
  {
    path: 'methods/melanoma-spatial-immunoediting-workflow.md',
    meta: {
      type: 'method',
      id: 'melanoma-spatial-immunoediting-workflow',
      title: '原位黑色素瘤空间免疫编辑复刻流程',
      status: 'draft',
      method_kind: 'workflow',
      tags: ['paper-replication'],
      favorite: false,
      inputs: [],
      outputs: [],
      source: { kind: 'written' },
      license: 'CC-BY-NC-ND',
      cite: [],
      summary: 'Nirmal et al., Cancer Discovery 2022',
    },
    figure_refs: [],
  },
];

// 1. Build items across actions, papers, templates, and methods
const items = buildSpotlightItems(mockPages, () => {});
assert.ok(items.some((i) => i.group === '快速操作' && i.href === '#/gallery'));
assert.ok(items.some((i) => i.group === '论文复刻' && i.href === '#/papers/melanoma-spatial-immunoediting-workflow'));
assert.ok(items.some((i) => i.group === '绘图模版' && i.badge === 'Cancer Discovery'));
assert.ok(items.some((i) => i.group === '分析方法' && i.title === '细胞类型注释'));

// 2. Fuzzy token filtering matches journal_style and paper workflow
const cdMatches = filterSpotlightItems(items, 'Cancer Discovery');
assert.ok(cdMatches.some((i) => i.id === 'tpl-tri-panel-stage-umap'));
assert.ok(cdMatches.some((i) => i.id === 'paper-melanoma-spatial-immunoediting-workflow'));

// 3. Closed renders empty, open renders accessible Spotlight dialog
assert.equal(renderToStaticMarkup(<SpotlightPalette open={false} onClose={() => {}} pages={mockPages} onReload={() => {}} />), '');
const html = renderToStaticMarkup(<SpotlightPalette open={true} onClose={() => {}} pages={mockPages} onReload={() => {}} />);
assert.match(html, /Spotlight 快速检索/);
assert.match(html, /三联演进分期 UMAP/);
assert.match(html, /原位黑色素瘤空间免疫编辑复刻流程/);

console.log('apple-spotlight.test.tsx: 3/3 PASS');
