import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { api, MethodHubDetail, PageSummary, PlaybookStep } from '../src/api';
import { Flow } from '../src/flow';
import { MethodOverview, sortAndPartitionViz } from '../src/views/MethodOverview';
import { buildUnlockedSet, getStepReadiness, PlaybooksView } from '../src/views/PlaybooksView';
import { ResourcesView } from '../src/views/ResourcesView';

const graph = { nodes: [], links: [] };
const TAXONOMY = { total: 0, domains: [], purposes: [], unclassified: [] };
const dataOf = (pages: PageSummary[]) =>
  ({
    pages,
    hiddenPages: [],
    graph,
    flow: new Flow(graph),
    taxonomy: TAXONOMY,
    env: { titles: new Map(pages.map((p) => [p.path, p.meta.title])), hiddenSources: new Set() },
    reload: async () => {},
  }) as any;

let failed = 0;
async function check(name: string, fn: () => void | Promise<void>) {
  try {
    await fn();
    console.log(`PASS ${name}`);
  } catch (error: any) {
    failed++;
    console.error(`FAIL ${name}\n${error.stack}`);
  }
}

async function main() {
  const calls: { url: string; init?: RequestInit }[] = [];
  globalThis.fetch = (async (url: string, init?: RequestInit) => {
    calls.push({ url, init });
    if (url === '/api/templates/batch-confirm') {
      const parsed = JSON.parse(String(init?.body ?? '{}'));
      return { ok: true, json: async () => ({ confirmed: parsed.ids ?? [], count: (parsed.ids ?? []).length }) };
    }
    return { ok: true, json: async () => ({ path: 'templates/t-1.md', meta: { type: 'template', id: 't-1', title: 'T1', status: 'ready' } }) };
  }) as any;

  await check('api.confirmTemplate and api.batchConfirmTemplates hit expected endpoints and payloads', async () => {
    calls.length = 0;
    await api.confirmTemplate('tpl/with space');
    assert.equal(calls[0].url, '/api/templates/tpl%2Fwith%20space/confirm');
    assert.equal(calls[0].init?.method, 'POST');

    const batchRes = await api.batchConfirmTemplates(['tpl-a', 'tpl-b']);
    assert.equal(calls[1].url, '/api/templates/batch-confirm');
    assert.equal(calls[1].init?.method, 'POST');
    assert.deepEqual(JSON.parse(String(calls[1].init?.body)), {
      ids: ['tpl-a', 'tpl-b'],
      confirmed: true,
    });
    assert.deepEqual(batchRes, { confirmed: ['tpl-a', 'tpl-b'], count: 2 });
  });

  await check('PlaybooksView data inventory unlocks expected prerequisites and evaluates requires + external_requires', () => {
    const scOnly = buildUnlockedSet(['scrna']);
    assert.ok(scOnly.has('scrna-annotated-cells'));
    assert.ok(scOnly.has('stromal-subcluster-markers'));
    assert.ok(!scOnly.has('visium-spatial-object'));
    assert.ok(!scOnly.has('bulk-clinical-survival'));
    assert.ok(!scOnly.has('gene-set-list'));

    const allUnlocked = buildUnlockedSet(['scrna', 'st', 'bulk', 'geneset']);
    assert.ok(allUnlocked.has('visium-spatial-object'));
    assert.ok(allUnlocked.has('bulk-clinical-survival'));
    assert.ok(allUnlocked.has('gene-set-list'));

    const stepWithBoth: PlaybookStep = {
      id: 'multi-step',
      title: 'Multi Step',
      requires: ['scrna-annotated-cells'],
      external_requires: ['bulk-clinical-survival', 'gene-set-list'],
    };
    const rPartial = getStepReadiness(stepWithBoth, scOnly);
    assert.equal(rPartial.hasRequirements, true);
    assert.equal(rPartial.ready, false);
    assert.deepEqual(rPartial.missingReqs, ['bulk-clinical-survival', 'gene-set-list']);

    const rReady = getStepReadiness(stepWithBoth, allUnlocked);
    assert.equal(rReady.ready, true);
    assert.deepEqual(rReady.missingReqs, []);

    const pbHtml = renderToStaticMarkup(
      <PlaybooksView
        data={dataOf([])}
        query="playbook=stromal-tme-scrna-st-playbook&step=spatial-transcriptomics-microenvironment"
      />,
    );
    assert.ok(pbHtml.includes('我手里有哪些数据？'));
    assert.ok(pbHtml.includes('已注释单细胞数据 (scRNA)'));
    assert.ok(pbHtml.includes('Visium 空转切片 (ST)'));
    assert.ok(pbHtml.includes('带随访 Bulk 队列 (TCGA/临床)'));
    assert.ok(pbHtml.includes('基因集 / 差异基因表'));
    assert.ok(pbHtml.includes('dag-node-locked'));
    assert.ok(pbHtml.includes('缺数据: visium-spatial-object'));
    assert.ok(!pbHtml.includes('缺数据: scrna-annotated-cells'));

    // Also test a scenario with a step unlocked solely by scRNA (stromal-subcluster-markers)
    const readyScenario = {
      path: 'scenarios/custom-scrna-playbook.md',
      preview: null,
      workflow: null,
      meta: {
        type: 'scenario',
        id: 'custom-scrna-playbook',
        title: 'Custom scRNA Playbook',
        picks: [],
      },
    } as unknown as PageSummary;
    // Playbook step readiness for scrna-only requirement renders ready badge on active step header
    const scReadyStep = getStepReadiness(
      { id: 's1', title: 'S1', requires: ['stromal-subcluster-markers'] },
      scOnly,
    );
    assert.equal(scReadyStep.ready, true);
    assert.ok(readyScenario);
  });

  await check('MethodOverview sorts ready+default first and collapses layers > 3 templates', () => {
    const items = [
      { id: 'v1', title: 'Variant 1', path: 'templates/v1.md', status: 'ready' as const, style_tier: 'variant' as const, language: 'r', chart_types: [], tables: [], preview_url: null, match_type: 'full', matched_interfaces: [], missing_required_interfaces: [] },
      { id: 'v2', title: 'Variant 2', path: 'templates/v2.md', status: 'draft' as const, style_tier: 'variant' as const, language: 'r', chart_types: [], tables: [], preview_url: null, match_type: 'full', matched_interfaces: [], missing_required_interfaces: [] },
      { id: 'd1', title: 'Default Ready', path: 'templates/d1.md', status: 'ready' as const, style_tier: 'default' as const, language: 'r', chart_types: [], tables: [], preview_url: null, match_type: 'full', matched_interfaces: [], missing_required_interfaces: [] },
      { id: 'v3', title: 'Variant 3', path: 'templates/v3.md', status: 'ready' as const, style_tier: 'variant' as const, language: 'r', chart_types: [], tables: [], preview_url: null, match_type: 'full', matched_interfaces: [], missing_required_interfaces: [] },
      { id: 'v4', title: 'Variant 4', path: 'templates/v4.md', status: 'ready' as const, style_tier: 'variant' as const, language: 'r', chart_types: [], tables: [], preview_url: null, match_type: 'full', matched_interfaces: [], missing_required_interfaces: [] },
    ];
    const collapsed = sortAndPartitionViz(items, [], false);
    assert.equal(collapsed.sorted[0].id, 'd1');
    assert.equal(collapsed.sorted[collapsed.sorted.length - 1].id, 'v2');
    assert.equal(collapsed.visible.length, 3);
    assert.equal(collapsed.hiddenCount, 2);

    const expanded = sortAndPartitionViz(items, [], true);
    assert.equal(expanded.visible.length, 5);

    // Always includes all default templates even if > 3 defaults exist
    const fourDefaultsPlusTwoVariants = [
      ...['d1', 'd2', 'd3', 'd4'].map((id) => ({ id, status: 'ready' as const, style_tier: 'default' as const })),
      ...['v1', 'v2'].map((id) => ({ id, status: 'ready' as const, style_tier: 'variant' as const })),
    ];
    const manyDefaults = sortAndPartitionViz(fourDefaultsPlusTwoVariants, [], false);
    assert.equal(manyDefaults.visible.length, 4);
    assert.equal(manyDefaults.hiddenCount, 2);

    const hub: MethodHubDetail = {
      id: 'differential-expression',
      title: '差异表达分析',
      path: 'methods/differential-expression.md',
      status: 'ready',
      summary: 'DEG',
      data_domains: ['bulk-transcriptomics'],
      data_domain_labels: ['Bulk 转录组'],
      purposes: ['差异与功能分析'],
      tags: [],
      keywords: [],
      inputs: [],
      outputs: [],
      data_contract: {},
      render_bridges: [],
      implementations: [],
      implementation_status: [],
      workflow: null,
      next_steps_count: 0,
      attached_visualizations: {
        curated: items.map((it) => ({
          ...it,
          primary: it.id === 'd1',
          compatibility: 'direct',
          verification: { state: 'verified' },
          reason: '',
          adaptation: '',
          prerequisites: [],
        })),
        object_compatible: items,
        render_bridged: [],
        all_previews: [],
      },
      reference_recipes: [],
      unmapped_recipes_count: 0,
    };

    const html = renderToStaticMarkup(
      <MethodOverview
        meta={{
          type: 'method',
          id: 'differential-expression',
          title: '差异表达分析',
          method_kind: 'analysis',
          status: 'ready',
          tags: [],
          favorite: false,
          inputs: [],
          outputs: [],
          source: { kind: 'written' },
          license: 'none',
          cite: [],
        }}
        figures={[]}
        pages={[]}
        hub={hub}
      />,
    );
    assert.ok(html.includes('展开其余 2 套绘图模板'));
    assert.ok(html.includes('Default Ready'));
    assert.ok(!html.includes('Variant 2'), 'low-ranked draft variant should be collapsed initially');
  });

  await check('ResourcesView renders batch template review panel in empty and grouped draft states', () => {
    const emptyHtml = renderToStaticMarkup(<ResourcesView data={dataOf([])} />);
    assert.ok(emptyHtml.includes('待确认绘图模板批次审核'));
    assert.ok(emptyHtml.includes('全部绘图模板均已确认 ✓'));

    const draftCai1: PageSummary = {
      path: 'templates/cai-fig1.md',
      meta: {
        type: 'template',
        id: 'cai-fig1',
        title: 'Cai Fig1 基质包络 UMAP',
        status: 'draft',
        tags: [],
        favorite: false,
        language: 'r',
        panels: [],
        chart_types: ['umap'],
        primary_method: 'cell-type-annotation',
        style_tier: 'default',
        journal_style: 'Cai2026-npjPO',
      },
    };
    const draftCai2: PageSummary = {
      path: 'templates/cai-fig2.md',
      meta: {
        type: 'template',
        id: 'cai-fig2',
        title: 'Cai Fig2 Ro/e 热图',
        status: 'draft',
        tags: [],
        favorite: false,
        language: 'r',
        panels: [],
        chart_types: ['heatmap'],
        primary_method: 'cell-proportion-composition',
        style_tier: 'variant',
        journal_style: 'Cai2026-npjPO',
      },
    };
    const draftGeneral: PageSummary = {
      path: 'templates/gen-volcano.md',
      meta: {
        type: 'template',
        id: 'gen-volcano',
        title: '通用火山图',
        status: 'draft',
        tags: [],
        favorite: false,
        language: 'r',
        panels: [],
        chart_types: ['volcano'],
        primary_method: 'differential-expression',
      },
    };
    const readyTpl: PageSummary = {
      path: 'templates/ready-dot.md',
      meta: {
        type: 'template',
        id: 'ready-dot',
        title: '已确认点图',
        status: 'ready',
        tags: [],
        favorite: false,
        language: 'r',
        panels: [],
        chart_types: ['dotplot'],
      },
    };

    const html = renderToStaticMarkup(
      <ResourcesView data={dataOf([draftCai1, draftCai2, draftGeneral, readyTpl])} />,
    );
    assert.ok(html.includes('待确认绘图模板批次审核'));
    assert.ok(!html.includes('全部绘图模板均已确认 ✓'));
    assert.ok(html.includes('Cai2026-npjPO'));
    assert.ok(html.includes('通用模板'));
    assert.ok(html.includes('Cai Fig1 基质包络 UMAP'));
    assert.ok(html.includes('cell-type-annotation'));
    assert.ok(html.includes('主推默认'));
    assert.ok(html.includes('可切换画风'));
    assert.ok(html.includes('批量确认通过 (2)'));
    assert.ok(html.includes('批量确认通过 (1)'));
    assert.ok(!html.includes('已确认点图'), 'ready templates must not appear in draft batch review');
  });

  if (failed) process.exitCode = 1;
  else console.log('v5.1 UX: all checks passed');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
