import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import {
  api,
  cachePages,
  evictCachedPage,
  hasCachedFacts,
  loadLibrary,
  MethodHubDetail,
  PageDetail,
  PageSummary,
  pageCache,
  previewOf,
  withThumbWidth,
  workflowOf,
} from '../src/api';
import { PlateCard } from '../src/components';
import { DeleteTemplateModal } from '../src/DeleteTemplateModal';
import { groupByOutputSlot, matchesFigureQuery, stylePillLabel } from '../src/figureModels';
import { Flow } from '../src/flow';
import { Gallery } from '../src/views/Gallery';
import { groupVizBySlot, MethodOverview } from '../src/views/MethodOverview';
import { PageView } from '../src/views/PageView';

const graph = { nodes: [], links: [] };
const TAXONOMY = { total: 0, domains: [], purposes: [], unclassified: [] };

const tplPage = (
  id: string,
  title: string,
  opts: {
    primary_method?: string;
    chart?: string;
    style_tier?: 'default' | 'variant';
    journal_style?: string;
    workflow_id?: string;
  } = {},
): PageSummary => ({
  path: `templates/${id}.md`,
  style_tier: opts.style_tier,
  journal_style: opts.journal_style,
  paper_origins: opts.workflow_id
    ? [{ workflow_id: opts.workflow_id, title: `${opts.workflow_id} 复刻流程` }]
    : undefined,
  meta: {
    type: 'template',
    id,
    title,
    status: 'ready',
    language: 'r',
    tags: ['single-cell'],
    favorite: false,
    panels: [],
    chart_types: [opts.chart ?? 'umap'],
    primary_method: opts.primary_method ?? 'cell-type-annotation',
    style_tier: opts.style_tier,
    journal_style: opts.journal_style,
  },
  preview: {
    url: `/files/wiki/templates/${id}/preview.png`,
    kind: 'replay',
    label: '模板回放',
  },
  workflow: { stage: 'complete', queue: null, label: '可用', reason: '', templates: [] },
});

const dataOf = (pages: PageSummary[]) =>
  ({
    pages,
    hiddenPages: [],
    graph,
    flow: new Flow(graph),
    taxonomy: TAXONOMY,
    env: { titles: new Map(pages.map((p) => [p.path, p.meta.title])), hiddenSources: new Set() },
    reload: async () => {},
    removePageLocally: () => {},
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
  await check('Output Slot grouping places default first, disambiguates duplicate journal styles, and renders Gallery switcher', () => {
    const tDefault = tplPage('scrna-celltype-umap', '单细胞细胞类型 UMAP（标准版）', {
      style_tier: 'default',
      journal_style: 'Standard',
    });
    const tCai = tplPage('stromal-hull-umap', '基质亚群功能包络UMAP', {
      style_tier: 'variant',
      journal_style: 'Cai2026-npjPO',
      workflow_id: 'cai-wf',
    });
    const tNirmal = tplPage('tri-panel-stage-umap', '三联分群分期患者 UMAP', {
      style_tier: 'variant',
      journal_style: 'Cancer Discovery',
      workflow_id: 'nirmal-wf',
    });
    const tOther = tplPage('marker-bubble-dotplot', '细胞类型 × 基因气泡点图', {
      chart: 'dotplot',
      style_tier: 'default',
      journal_style: 'Standard',
    });

    const groups = groupByOutputSlot([tNirmal, tCai, tOther, tDefault] as any);
    assert.equal(groups.length, 2);
    const umapGroup = groups.find((g) => g.slotKey === 'cell-type-annotation::umap')!;
    assert.equal(umapGroup.items.length, 3);
    assert.equal(umapGroup.defaultItem.meta.id, 'scrna-celltype-umap');

    // Disambiguate duplicate journal_style within one slot
    const dupSubjects = [
      { id: 'spatial-feature-grid', title: '空间转录组特征分布网格', style_tier: 'default' as const, journal_style: 'Cai2026-npjPO' },
      { id: 'spatial-coexpr-multichannel', title: '多通道空间表达与重点区域', style_tier: 'variant' as const, journal_style: 'Cai2026-npjPO' },
      { id: 'spatial-he-deconv-panel', title: '配准组织图与反卷积对照', style_tier: 'variant' as const, journal_style: 'Cai2026-npjPO' },
    ];
    assert.equal(stylePillLabel(dupSubjects[0], dupSubjects), 'Cai2026-npjPO 默认');
    assert.ok(stylePillLabel(dupSubjects[1], dupSubjects).includes('多通道空间表达'));
    assert.ok(stylePillLabel(dupSubjects[2], dupSubjects).includes('配准组织图'));

    const galleryHtml = renderToStaticMarkup(<Gallery data={dataOf([tNirmal, tCai, tDefault, tOther])} />);
    assert.ok(galleryHtml.includes('按输出槽位分组'));
    assert.ok(galleryHtml.includes('平铺全部'));
    assert.ok(galleryHtml.includes('共 <strong>2</strong> 个输出槽位'));
    assert.ok(galleryHtml.includes('Standard 默认'));
    assert.ok(galleryHtml.includes('Cai2026-npjPO'));
    assert.ok(galleryHtml.includes('Cancer Discovery'));
    // Multi-style slot renders Apple frosted capsule badge; single-style slot does not
    assert.ok(galleryHtml.includes('class="slot-count-badge">3 种画风</span>'));
    assert.ok(!galleryHtml.includes('1 种画风'));
    // Card PlateCard uses ?w=600 thumbnails
    assert.ok(galleryHtml.includes('/files/wiki/templates/scrna-celltype-umap/preview.png?w=600'));
    // Template PlateCard exposes safe delete button
    assert.ok(galleryHtml.includes('删除模版'));
  });

  await check('MethodOverview groups Output Slots with inline style switcher and ?w=600 thumbnails', () => {
    const pages = [
      tplPage('scrna-celltype-umap', '单细胞细胞类型 UMAP（标准版）', { style_tier: 'default', journal_style: 'Standard' }),
      tplPage('stromal-hull-umap', '基质亚群功能包络UMAP', { style_tier: 'variant', journal_style: 'Cai2026-npjPO' }),
    ];
    const hub: MethodHubDetail = {
      id: 'cell-type-annotation',
      title: '细胞类型注释',
      path: 'methods/cell-type-annotation.md',
      status: 'ready',
      summary: '注释方法',
      data_domains: ['single-cell'],
      data_domain_labels: ['单细胞转录组'],
      purposes: ['注释与参考映射'],
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
        curated: [
          {
            id: 'stromal-hull-umap',
            title: '基质亚群功能包络UMAP',
            path: 'templates/stromal-hull-umap.md',
            kind: 'template',
            status: 'ready',
            language: 'r',
            style_tier: 'variant',
            journal_style: 'Cai2026-npjPO',
            primary_method: 'cell-type-annotation',
            chart_types: ['umap'],
            tables: [{ key: 'cells', interface: '', description: 'cells', required: true }],
            preview_url: '/files/wiki/templates/stromal-hull-umap/preview.png',
            primary: true,
            compatibility: 'adaptable',
            verification: { state: 'not_run', scope: 'test' },
            reason: '',
            adaptation: '',
            prerequisites: [],
          },
          {
            id: 'scrna-celltype-umap',
            title: '单细胞细胞类型 UMAP（标准版）',
            path: 'templates/scrna-celltype-umap.md',
            kind: 'template',
            status: 'ready',
            language: 'r',
            style_tier: 'default',
            journal_style: 'Standard',
            primary_method: 'cell-type-annotation',
            chart_types: ['umap'],
            tables: [{ key: 'umap', interface: 'render-umap-groups', description: 'umap', required: true }],
            preview_url: '/files/wiki/templates/scrna-celltype-umap/preview.png',
            primary: true,
            compatibility: 'adaptable',
            verification: { state: 'not_run', scope: 'test' },
            reason: '',
            adaptation: '',
            prerequisites: [],
          },
        ],
        object_compatible: [],
        render_bridged: [],
        all_previews: [],
      },
      reference_recipes: [],
      unmapped_recipes_count: 0,
    };

    const grouped = groupVizBySlot(hub.attached_visualizations.curated, pages, 'cell-type-annotation');
    assert.equal(grouped.length, 1);
    assert.equal(grouped[0].defaultItem.id, 'scrna-celltype-umap');

    const html = renderToStaticMarkup(
      <MethodOverview meta={{ type: 'method', id: 'cell-type-annotation', title: '细胞类型注释', method_kind: 'analysis', status: 'ready', tags: [], favorite: false, inputs: [], outputs: [], source: { kind: 'written' }, license: 'MIT', cite: [] }} figures={[]} pages={pages} hub={hub} />,
    );
    assert.ok(html.includes('期刊画风 (2)'));
    assert.ok(html.includes('Standard 默认'));
    assert.ok(html.includes('Cai2026-npjPO'));
    assert.ok(html.includes('/files/wiki/templates/scrna-celltype-umap/preview.png?w=600'));
    assert.ok(html.includes('render-umap-groups'));
  });

  await check('withThumbWidth appends ?w=600 to wiki/gallery raster URLs only', () => {
    assert.equal(withThumbWidth('/files/wiki/templates/a/preview.png', 600), '/files/wiki/templates/a/preview.png?w=600');
    assert.equal(withThumbWidth('/files/gallery/g/fig01.png', 600), '/files/gallery/g/fig01.png?w=600');
    assert.equal(withThumbWidth('/files/wiki/templates/a/code.py', 600), '/files/wiki/templates/a/code.py');
    assert.equal(withThumbWidth('/files/wiki/templates/a/preview.png', null), '/files/wiki/templates/a/preview.png');
  });

  await check('App.tsx does not put route/hydrateLibrary into reload useEffect dependency loop', () => {
    const appSource = readFileSync(resolve(process.cwd(), 'src/App.tsx'), 'utf8');
    assert.ok(!appSource.includes('[hydrateLibrary]'), 'reload must not depend on hydrateLibrary');
    assert.ok(appSource.includes('hydratedRef'), 'App must track completed hydration');
    assert.ok(appSource.includes('hydratingRef'), 'App must track in-flight hydration separately from completed hydration');
    assert.ok(appSource.includes('removePageLocally'), 'AppData must expose removePageLocally');
    assert.ok(appSource.includes('evictCachedPage'), 'removePageLocally must evict preview/workflow caches');
    assert.ok(appSource.includes('generation.current++'), 'removePageLocally must supersede in-flight hydration generation');
    assert.ok(appSource.includes('mutationRevision'), 'App must bump mutationRevision so MethodHub consumers resync');
  });

  await check('matchesFigureQuery indexes journal_style and handles null chart_types/tags safely', () => {
    const tVariant = tplPage('tri-panel-stage-umap', '三联分群分期患者 UMAP', {
      style_tier: 'variant',
      journal_style: 'Cancer Discovery',
    });
    assert.equal(matchesFigureQuery(tVariant.meta as any, 'Cancer Discovery', [tVariant]), true);
    assert.equal(matchesFigureQuery(tVariant.meta as any, 'cancer', [tVariant]), true);

    const legacyNullCharts = {
      path: 'templates/legacy-null.md',
      meta: {
        ...tVariant.meta,
        id: 'legacy-null',
        title: '旧版空图型模板',
        chart_types: undefined,
        tags: undefined,
        journal_style: 'Nature Medicine',
      },
    } as any;
    assert.equal(matchesFigureQuery(legacyNullCharts.meta, 'Nature Medicine', [legacyNullCharts]), true);
    assert.doesNotThrow(() => groupByOutputSlot([legacyNullCharts]));
    assert.equal(groupByOutputSlot([legacyNullCharts])[0].slotKey, 'single::templates/legacy-null.md');

    const galleryHtml = renderToStaticMarkup(<Gallery data={dataOf([tVariant, legacyNullCharts])} />);
    assert.ok(galleryHtml.includes('旧版空图型模板'));
  });

  await check('slotItemRank prefers default→unset→variant, then ready, then id ascending', () => {
    const mk = (id: string, status: 'ready' | 'draft', style_tier?: 'default' | 'variant') => ({
      ...tplPage(id, id, { style_tier }),
      meta: { ...tplPage(id, id, { style_tier }).meta, status },
    });
    const group = groupByOutputSlot([
      mk('z-variant-ready', 'ready', 'variant'),
      mk('a-variant-draft', 'draft', 'variant'),
      mk('b-unset-ready', 'ready', undefined),
      mk('m-default-draft', 'draft', 'default'),
    ] as any)[0];
    assert.deepEqual(
      group.items.map((it) => it.meta.id),
      ['m-default-draft', 'b-unset-ready', 'z-variant-ready', 'a-variant-draft'],
    );
  });

  await check('evictCachedPage clears pageCache, previewCache, and workflowCache, and loadLibrary reports hydration success/failure', async () => {
    const tpl = tplPage('evict-me', '待删除模板');
    const detail: PageDetail = {
      ...tpl,
      body: '# 待删除模板',
      backlinks: [],
      gallery: null,
    };
    cachePages([tpl]);
    pageCache.set(tpl.path, detail);
    assert.equal(hasCachedFacts(tpl.meta), true);
    assert.ok(previewOf(tpl.meta));
    assert.ok(workflowOf(tpl.meta));

    evictCachedPage(tpl.path, tpl.meta);
    assert.equal(pageCache.has(tpl.path), false);
    assert.equal(hasCachedFacts(tpl.meta), false);
    assert.equal(previewOf(tpl.meta), null);
    assert.equal(workflowOf(tpl.meta), null);

    // Also evicts by path alone when meta is omitted
    cachePages([tpl]);
    pageCache.set(tpl.path, detail);
    evictCachedPage(tpl.path);
    assert.equal(pageCache.has(tpl.path), false);
    assert.equal(hasCachedFacts(tpl.meta), false);

    // loadLibrary returns false when graph fails (allowing cold-route retry on next navigation), true when all succeed
    const prevFetch = globalThis.fetch;
    try {
      let graphFail = true;
      globalThis.fetch = (async (url: string) => {
        if (url.startsWith('/api/pages')) return { ok: true, json: async () => [tpl] };
        if (url === '/api/graph') {
          if (graphFail) return { ok: false, statusText: 'boom', json: async () => ({ detail: 'graph down' }) };
          return { ok: true, json: async () => ({ nodes: [], links: [] }) };
        }
        if (url === '/api/method-taxonomy') return { ok: true, json: async () => TAXONOMY };
        return { ok: true, json: async () => ({}) };
      }) as any;

      const errors: string[] = [];
      const firstOk = await loadLibrary(
        { pages: () => {}, graph: () => {}, taxonomy: () => {}, error: (m) => errors.push(m) },
        () => true,
        true,
      );
      assert.equal(firstOk, false);
      assert.deepEqual(errors, ['graph down']);

      graphFail = false;
      const retryOk = await loadLibrary(
        { pages: () => {}, graph: () => {}, taxonomy: () => {}, error: (m) => errors.push(m) },
        () => true,
        true,
      );
      assert.equal(retryOk, true);

      // Superseded generation returns false
      const supersededOk = await loadLibrary(
        { pages: () => {}, graph: () => {}, taxonomy: () => {} },
        () => false,
        true,
      );
      assert.equal(supersededOk, false);
    } finally {
      globalThis.fetch = prevFetch;
    }
  });

  await check('1-click active template deletion API, DeleteTemplateModal, PageView and PlateCard buttons work cleanly', async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    globalThis.fetch = (async (url: string, init?: RequestInit) => {
      calls.push({ url, init });
      if (url.includes('/delete-plan')) {
        return {
          ok: true,
          json: async () => ({
            title: 'T1',
            path: 'templates/t-1.md',
            revision: 'rev1',
            asset_files: 3,
            affected: [{ path: 'methods/m.md', title: 'Method M', figure_relations_removed: 1 }],
            figure_relations_removed: 1,
            layout_files_updated: [],
            slot_default_warning: {
              primary_method: 'cell-type-annotation',
              chart_type: 'umap',
              recommended_successor: 't-2',
              remaining_variants: ['t-2'],
              message: '建议将 t-2 设为新的 default。',
            },
            gallery_preserved: true,
          }),
        };
      }
      return { ok: true, json: async () => ({ deleted: true, audit: 'deletion-records/a.json' }) };
    }) as any;

    const plan = await api.deletePlan('templates', 't-1', true);
    assert.equal(calls[0].url, '/api/templates/t-1/delete-plan?allow_active=true');
    assert.equal(plan.slot_default_warning?.recommended_successor, 't-2');

    const del = await api.deleteArchived('templates', 't-1', 'rev1', true);
    assert.equal(calls[1].url, '/api/templates/t-1/delete');
    assert.deepEqual(JSON.parse(String(calls[1].init?.body)), { confirmed: true, revision: 'rev1', allow_active: true });
    assert.equal(del.deleted, true);

    const modalHtml = renderToStaticMarkup(
      <DeleteTemplateModal
        templateId="t-1"
        templateTitle="模板一"
        templatePath="templates/t-1.md"
        onClose={() => {}}
        onDeleted={() => {}}
      />,
    );
    assert.ok(modalHtml.includes('安全删除绘图模版'));
    assert.ok(modalHtml.includes('templates/t-1.md'));

    const page: PageDetail = {
      ...tplPage('t-1', '模板一', { style_tier: 'default', journal_style: 'Standard' }),
      body: '# 模板一\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n',
      backlinks: [],
      gallery: null,
    };
    pageCache.set(page.path, page);
    const pageHtml = renderToStaticMarkup(<PageView path={page.path} data={dataOf([page])} />);
    assert.ok(pageHtml.includes('删除模版'));
    // Detail page viewer must keep full-resolution original image (no ?w=600)
    assert.ok(pageHtml.includes('src="/files/wiki/templates/t-1/preview.png"'));
    assert.ok(!pageHtml.includes('src="/files/wiki/templates/t-1/preview.png?w=600"'));

    const cardHtml = renderToStaticMarkup(
      <PlateCard
        path={page.path}
        meta={page.meta as any}
        number={1}
        onRequestDelete={() => {}}
      />,
    );
    assert.ok(cardHtml.includes('删除模版'));
    assert.ok(cardHtml.includes('preview.png?w=600'));
  });

  if (failed > 0) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
