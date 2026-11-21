import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { api, PaperDetail, PaperSummary, PageSummary } from '../src/api';
import { PlateCard } from '../src/components';
import { Flow } from '../src/flow';
import { MethodOverview } from '../src/views/MethodOverview';
import { buildPanelRunCommand, evidenceBadgeMeta, PaperDetailSection, PaperListSection, panelReceiptLabel } from '../src/views/PapersView';

const graph = { nodes: [], links: [] };
const TAXONOMY = { total: 0, domains: [], purposes: [], unclassified: [] };

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
    return { ok: true, json: async () => ({}) };
  }) as any;

  await check('api.papers, api.paper, and api.paperPanelCode build expected URLs', async () => {
    calls.length = 0;
    await api.papers();
    await api.paper('breast-cancer-stromal-tme-workflow');
    await api.paperPanelCode('breast-cancer-stromal-tme-workflow', 'code/panels/fig01_b.R');
    assert.equal(calls[0].url, '/api/papers');
    assert.equal(calls[1].url, '/api/papers/breast-cancer-stromal-tme-workflow');
    assert.equal(
      calls[2].url,
      '/api/papers/breast-cancer-stromal-tme-workflow/panel-code?path=code%2Fpanels%2Ffig01_b.R',
    );
  });

  await check('PaperListSection and PaperDetailSection render 1:1 figures, tier badges, and CLI run commands', () => {
    const papers: PaperSummary[] = [
      {
        workflow_id: 'breast-cancer-stromal-tme-workflow',
        title: '乳腺癌基质单细胞与空转微环境复刻流程',
        summary: 'Cai 2026 复刻流程',
        paper_id: '2026-cai-stromal-tme',
        doi: '10.1038/s41698-026-01718-1',
        journal: 'npj Precision Oncology',
        year: 2026,
        license: 'CC-BY-NC-ND-4.0',
        upstream_repo: 'https://github.com/qingyaolab/breastcancer-Stromal-Cell',
        workflow_page: 'methods/breast-cancer-stromal-tme-workflow.md',
        project_page: 'projects/2026-cai-stromal-tme.md',
        gallery_entry: '2026-11-19-cai-stromal-tme',
        cover_url: '/files/gallery/2026-11-19-cai-stromal-tme/figures/fig01_replica.png',
        figure_count: 12,
        has_receipts: true,
        stats: {
          figures: 12,
          panels: 74,
          original_table: 24,
          local_recompute: 34,
          proxy: 12,
          excluded_wet_lab: 3,
          excluded_schematic: 1,
          excluded_imaging: 0,
          excluded_total: 4,
          computed: 70,
          templates: 18,
        },
      },
    ];
    const listHtml = renderToStaticMarkup(<PaperListSection papers={papers} />);
    assert.ok(listHtml.includes('论文复刻展示栏'));
    assert.ok(listHtml.includes('npj Precision Oncology'));
    assert.ok(listHtml.includes('10.1038/s41698-026-01718-1'));
    assert.ok(listHtml.includes('计算复现 70'));
    assert.ok(listHtml.includes('#/papers/breast-cancer-stromal-tme-workflow'));

    const detail: PaperDetail = {
      ...papers[0],
      upstream_commit: '95118a8cc89f',
      excluded_wet_lab: ['Fig. 3F', 'Fig. 3G', 'Fig. 3H'],
      receipts_summary: { present: true, generated_at: '2026-11-20T10:00:00Z', count: 70 },
      runtime: null,
      figures: [
        {
          slug: 'fig01',
          label: 'Fig. 1',
          caption: 'Stromal atlas',
          is_supplementary: false,
          declared_panels: ['A', 'B'],
          replica_url: '/files/gallery/2026-11-19-cai-stromal-tme/figures/fig01_replica.png',
          side_by_side_url: '/files/gallery/2026-11-19-cai-stromal-tme/figures/fig01_side_by_side.png',
          replica_px: [2880, 3660],
          side_by_side_px: [2061, 1338],
          visual_review: 'PASS',
          panels: [
            {
              panel_key: 'fig01/A',
              figure_slug: 'fig01',
              figure: 'Fig. 1',
              panel_letter: 'A',
              panel: '1A',
              evidence_tier: 'excluded_schematic',
              is_excluded: true,
              description: '研究设计流程示意图',
              note: '',
              script_path: '',
              script_available: false,
              code_url: null,
              input_tables: [],
              methods: [],
              template_id: null,
              template: null,
              extra_templates: [],
            },
            {
              panel_key: 'fig01/B',
              figure_slug: 'fig01',
              figure: 'Fig. 1',
              panel_letter: 'B',
              panel: '1B',
              evidence_tier: 'local_recompute',
              is_excluded: false,
              description: '三大区室 UMAP',
              note: '',
              script_path: 'code/panels/fig01_b.R',
              script_available: true,
              code_url: '/api/papers/breast-cancer-stromal-tme-workflow/panel-code?path=code%2Fpanels%2Ffig01_b.R',
              input_tables: ['stromal_umap.csv'],
              methods: ['cell-type-annotation'],
              template_id: 'stromal-hull-umap',
              template: {
                id: 'stromal-hull-umap',
                title: '基质亚群功能包络UMAP',
                path: 'templates/stromal-hull-umap.md',
                status: 'ready',
                language: 'r',
                style_tier: 'variant',
                journal_style: 'Cai2026-npjPO',
                chart_types: ['umap'],
                preview_url: '/files/wiki/templates/stromal-hull-umap/preview.png',
              },
              extra_templates: [],
              receipt: { status: 'pass' },
            },
          ],
        },
      ],
    };

    const detailHtml = renderToStaticMarkup(<PaperDetailSection detail={detail} />);
    assert.ok(detailHtml.includes('1:1 复刻大图'));
    assert.ok(detailHtml.includes('原图并排对照'));
    assert.ok(detailHtml.includes('示意图已排除'));
    assert.ok(detailHtml.includes('本地重算'));
    assert.ok(detailHtml.includes('跨论文复用示例'));
    assert.ok(detailHtml.includes('查看独立代码'));

    assert.equal(evidenceBadgeMeta('excluded_imaging').label, '显微影像已排除');
    assert.equal(
      buildPanelRunCommand('code/panels/fig01_b.R', 'fig01/B'),
      'Rscript --vanilla code/panels/fig01_b.R --paper-root <PAPER_ROOT> --out fig01_B.png',
    );
    // Legacy detail payload without new hash_matched fields must never claim "已验" or "verified"
    assert.ok(!detailHtml.includes('Panel 收据已验'));
    assert.ok(detailHtml.includes('已记录 70 条 Panel 收据（未含哈希核对）'));
  });

  await check('PapersView renders honest receipt hash/smoke counts and distinguishes manifest-only figures', () => {
    const paper: PaperSummary = {
      workflow_id: 'melanoma-spatial-immunoediting-workflow',
      title: '黑色素瘤空间免疫编辑复刻流程',
      summary: 'Nirmal 2022 复刻',
      paper_id: '2022-nirmal-melanoma-spatial',
      doi: '10.1158/2159-8290.CD-21-1357',
      journal: 'Cancer Discovery',
      year: 2022,
      license: 'CC-BY-NC-ND-4.0',
      upstream_repo: 'https://github.com/labsyspharm/melanoma-spatial',
      workflow_page: 'methods/melanoma-spatial-immunoediting-workflow.md',
      project_page: 'projects/2022-nirmal-melanoma-spatial.md',
      gallery_entry: '2026-11-20-nirmal-melanoma-spatial',
      cover_url: '/files/gallery/2026-11-20-nirmal-melanoma-spatial/figures/fig01_replica.png',
      figure_count: 13,
      reproduced_figure_count: 13,
      manifest_only_figures: [{ slug: 'sfig04', label: 'Fig. S4' }],
      has_receipts: true,
      receipt_counts: {
        total: 70,
        generated: 61,
        smoke_tested: 9,
        hash_checked: 70,
        hash_matched: 70,
      },
      stats: {
        figures: 14,
        panels: 105,
        original_table: 20,
        local_recompute: 30,
        proxy: 10,
        excluded_wet_lab: 10,
        excluded_schematic: 5,
        excluded_imaging: 30,
        excluded_total: 45,
        computed: 60,
        templates: 3,
      },
    };

    const listHtml = renderToStaticMarkup(<PaperListSection papers={[paper]} />);
    assert.ok(listHtml.includes('已核对代码哈希 70/70（其中 9 个已冒烟实跑）'));
    assert.ok(listHtml.includes('复刻整图 13'));
    assert.ok(listHtml.includes('仅清单排除 1（Fig. S4）'));
    assert.ok(!listHtml.includes('收据已验'));

    const detail: PaperDetail = {
      ...paper,
      upstream_commit: 'abc123',
      excluded_wet_lab: [],
      reproduced_figure_count: 1,
      manifest_only_figure_count: 1,
      receipts_summary: {
        present: true,
        generated_at: '2026-11-20T12:00:00Z',
        count: 70,
        total: 70,
        generated: 61,
        smoke_tested: 9,
        hash_checked: 70,
        hash_matched: 70,
        hash_mismatched: 0,
        script_missing: 0,
        status_counts: { generated: 61, smoke_tested: 9 },
      },
      runtime: null,
      figures: [
        {
          slug: 'sfig04',
          label: 'Fig. S4',
          caption: 'Pure CyCIF microscopy imaging panels',
          is_supplementary: true,
          declared_panels: ['A', 'B'],
          replica_url: null,
          side_by_side_url: null,
          replica_px: [],
          side_by_side_px: [],
          visual_review: '',
          manifest_only: true,
          panels: [
            {
              panel_key: 'sfig04/A',
              figure_slug: 'sfig04',
              figure: 'Fig. S4',
              panel_letter: 'A',
              panel: 'S4A',
              evidence_tier: 'excluded_imaging',
              is_excluded: true,
              description: 'CyCIF raw microscopy field',
              note: '',
              script_path: '',
              script_available: false,
              code_url: null,
              input_tables: [],
              methods: [],
              template_id: null,
              template: null,
              extra_templates: [],
            },
          ],
        },
        {
          slug: 'fig01',
          label: 'Fig. 1',
          caption: 'Main figure',
          is_supplementary: false,
          declared_panels: ['A'],
          replica_url: '/files/gallery/2026-11-20-nirmal-melanoma-spatial/figures/fig01_replica.png',
          side_by_side_url: null,
          replica_px: [2000, 1600],
          side_by_side_px: [],
          visual_review: 'PASS',
          manifest_only: false,
          panels: [
            {
              panel_key: 'fig01/A',
              figure_slug: 'fig01',
              figure: 'Fig. 1',
              panel_letter: 'A',
              panel: '1A',
              evidence_tier: 'local_recompute',
              is_excluded: false,
              description: 'Main UMAP',
              note: '',
              script_path: 'code/panels/fig01_a.py',
              script_available: true,
              code_url: '/api/papers/melanoma-spatial-immunoediting-workflow/panel-code?path=code%2Fpanels%2Ffig01_a.py',
              input_tables: [],
              methods: [],
              template_id: null,
              template: null,
              extra_templates: [],
              receipt: { status: 'generated' },
            },
          ],
        },
      ],
    };

    const detailHtml = renderToStaticMarkup(<PaperDetailSection detail={detail} />);
    assert.ok(detailHtml.includes('已核对代码哈希 70/70（其中 9 个已冒烟实跑）'));
    assert.ok(detailHtml.includes('复刻整图 1'));
    assert.ok(detailHtml.includes('仅清单排除图组 1'));
    assert.ok(detailHtml.includes('仅清单排除'));
    assert.ok(detailHtml.includes('不生成 1:1 代码复刻整图'));
    assert.ok(!detailHtml.includes('收据已验'));
    assert.ok(!detailHtml.includes('verified'));

    assert.equal(panelReceiptLabel({ status: 'generated' }), '仅登记脚本（未冒烟实跑）');
    assert.equal(panelReceiptLabel({ status: 'smoke_tested' }), '已冒烟实跑');
    assert.equal(panelReceiptLabel({}), '已登记收据（状态未知）');
  });

  await check('PlateCard and MethodOverview render cross-paper badge and link when paper_origins present', () => {
    const origins = [{ workflow_id: 'breast-cancer-stromal-tme-workflow', title: '乳腺癌基质复刻流程' }];
    const tplPage: PageSummary = {
      path: 'templates/stromal-hull-umap.md',
      paper_origins: origins,
      meta: {
        type: 'template',
        id: 'stromal-hull-umap',
        title: '基质亚群功能包络UMAP',
        status: 'ready',
        tags: ['single-cell'],
        chart_types: ['umap'],
        panels: [],
        language: 'r',
        favorite: false,
      },
    };
    const cardHtml = renderToStaticMarkup(
      <PlateCard path={tplPage.path} meta={tplPage.meta as any} number={1} paperOrigins={origins} />,
    );
    assert.ok(cardHtml.includes('跨论文复用示例'));
    assert.ok(cardHtml.includes('查看论文 1:1 整图'));
    assert.ok(cardHtml.includes('#/papers/breast-cancer-stromal-tme-workflow'));

    const methodHtml = renderToStaticMarkup(
      <MethodOverview
        meta={{
          type: 'method',
          id: 'cell-type-annotation',
          title: '细胞类型注释',
          status: 'ready',
          method_kind: 'analysis',
          tags: [],
          inputs: [],
          outputs: [],
          source: { kind: 'written' },
          license: 'MIT',
          cite: [],
          favorite: false,
        }}
        figures={[]}
        pages={[tplPage]}
        hub={{
          id: 'cell-type-annotation',
          title: '细胞类型注释',
          path: 'methods/cell-type-annotation.md',
          status: 'ready',
          summary: '',
          data_domains: [],
          data_domain_labels: [],
          purposes: [],
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
                status: 'ready',
                language: 'r',
                chart_types: ['umap'],
                tables: [],
                preview_url: null,
                primary: true,
                compatibility: 'adaptable',
                verification: { state: 'not_run' },
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
        }}
      />,
    );
    assert.ok(methodHtml.includes('跨论文复用示例'));
    assert.ok(methodHtml.includes('查看论文 1:1 整图'));
  });

  if (failed > 0) process.exit(1);
}

void main();
