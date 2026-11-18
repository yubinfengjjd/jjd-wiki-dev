import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { api, effectiveStatus, isItem, KIND_OF, pageCache, STATUS_LABEL, TYPE_LABEL } from '../src/api';
import { HAS_STATUS, TYPE_COLOR, TYPE_SHAPE } from '../src/palette';
import { Flow } from '../src/flow';
import { galleryEntries, templateSourceNote } from '../src/figureModels';
import { escapeTableWikilinks, renderBody } from '../src/markdown';
import { isNonCommercial, licenseLabel, recipeOrigin, resolvePick } from '../src/recipes';
import { Gallery, PlottingCodeShelf } from '../src/views/Gallery';
import { PageView } from '../src/views/PageView';
import { PlaybooksView } from '../src/views/PlaybooksView';
import { ProjectsView } from '../src/views/ProjectsView';
import { RecipesView } from '../src/views/RecipesView';
import { ResourcesView } from '../src/views/ResourcesView';
import { ScenariosView } from '../src/views/ScenariosView';
import { StudioView } from '../src/views/StudioView';

const graph = { nodes: [], links: [] };
const TAXONOMY = { total: 0, domains: [], purposes: [], unclassified: [] };
const dataOf = (pages) => ({ pages, hiddenPages: [], graph, flow: new Flow(graph), taxonomy: TAXONOMY,
  env: { titles: new Map(pages.map((p) => [p.path, p.meta.title])), hiddenSources: new Set() }, reload: async () => {} }) as any;

const recipeMeta = (id: string, extra: Record<string, unknown> = {}) => ({
  type: 'recipe', id, title: `火山图配方 ${id}`, status: 'draft', tags: ['转录组'], favorite: false,
  source: { id: 'figureya', item: `FigureYa59${id}`, commit: '0123456789abcdef0123', url: 'https://github.com/ying-ge/FigureYa' },
  license: 'CC-BY-NC-SA-4.0', cite: ['FigureYa 引用'], language: 'r', runner: 'rmd-knit', entry: 'source/main.Rmd',
  inputs: [{ file: 'easy_input.csv', note: '' }], outputs: ['volcano.pdf'],
  packages: { cran: ['ggplot2'], bioc: [], github: [], library: [] },
  keywords: ['volcano'], chart_types: ['volcano'], summary: '差异表达火山图', ...extra,
});
const flow = (stage: string, queue: string | null, label: string, reason = '') => ({ stage, queue, label, reason, templates: [] });
const noRun = { url: null, kind: 'none', label: '暂无运行图' };

{
  const html = renderToStaticMarkup(<Gallery data={dataOf([])} />);
  assert.ok(html.includes('绘图代码'), 'Gallery must expose reusable native/custom plot code separately from templates');
  const plot = {path: 'methods/plot-code.md', meta: {type: 'method',id:'plot-code',title:'依赖与自定义绘图',method_kind:'technical',status:'draft',tags:[],inputs:[],outputs:[],source:{kind:'written'},license:'none',cite:[],favorite:false,code_roles:['visualization'],implementations:[{id:'native-route',title:'irGSEA 原生热图',language:'R',entrypoint:'code/native.R:plot',dependencies:['irGSEA']}]},implementation_status:[{id:'native-route',state:'not_run',scope:'missing package'}]};
  const hidden = { ...plot, path:'methods/archived-plot.md', meta:{...plot.meta,id:'archived-plot',title:'已归档不展示',status:'archived'} };
  const shelf = renderToStaticMarkup(<PlottingCodeShelf data={dataOf([plot,plot,hidden])} query="irGSEA" />);
  assert.equal((shelf.match(/class="source-card method-code-card"/g) || []).length,1,'same code page appears once');
  assert.ok(shelf.includes('已验证 0/1') && shelf.includes('技术资料'));
  assert.ok(!shelf.includes('已归档不展示'));
}

const confirmable = { path: 'recipes/r-confirm.md', meta: recipeMeta('r-confirm'),
  preview: { url: '/files/wiki/recipes/r-confirm/preview.png', kind: 'replay', label: '原样运行图（最近一次通过）' },
  workflow: flow('recipe_confirm', 'confirm', '待你确认', '原样运行已通过；运行通过不等于科学有效。') };
const waiting = { path: 'recipes/r-work.md', meta: recipeMeta('r-work', { license: 'MIT' }), preview: noRun,
  workflow: flow('recipe_work', 'agent', '待装包', '最近运行为 not_run：ggplot2（装包须作者按批次批准一次）') };
const shelved = { path: 'recipes/r-old.md', meta: recipeMeta('r-old', { status: 'archived', archived_from: 'draft' }), preview: noRun,
  workflow: flow('archived', null, '已归档', '已归档，不进入待办。') };
const source = { path: 'sources/figureya.md', preview: null, workflow: null, meta: {
  type: 'source', id: 'figureya', title: 'FigureYa 来源库', url: 'https://github.com/ying-ge/FigureYa', commit: 'abc',
  license: 'CC-BY-NC-SA-4.0', license_notice: '', cite: [], adapter: 'figureya', trusted: false, snapshot: 'figureya',
  tags: [], keywords: [], summary: '' } };
const v2template = { path: 'templates/t-v2.md',
  preview: { url: '/files/wiki/recipes/r-confirm/preview.png', kind: 'source', label: '来源配方的原样运行图 · 模板尚无回放' },
  workflow: flow('template_work', 'agent', '待完成回放'),
  meta: { type: 'template', id: 't-v2', title: '派生火山图模板', status: 'draft', tags: [], favorite: false, language: 'r',
    sources: ['recipes/r-confirm'], panels: [], chart_types: ['volcano'] } };
const scenario = { path: 'scenarios/de.md', preview: null, workflow: null, meta: {
  type: 'scenario', id: 'de', title: '差异表达可视化', summary: '从 DE 表到火山图', tags: ['转录组'], keywords: [],
  picks: [{ id: 'recipes/r-confirm', note: '首选' }, { id: 't-v2', note: '' }, { id: 'figureya:FigureYa59volcanoV2', note: '目录项' },
    'methods/missing'] } };
const pages = [confirmable, waiting, shelved, source, v2template, scenario];

let failed = 0;
function check(name: string, fn: () => void | Promise<void>) {
  return Promise.resolve().then(fn).then(() => console.log(`PASS ${name}`),
    (error) => { failed++; console.error(`FAIL ${name}\n${error.stack}`); });
}
const detail = (page, body: string) => ({ ...page, body, backlinks: [], gallery: null, relations: [], implementation_status: [] });
const RECIPE_BODY = '# 火山图配方\n\n> CC BY-NC-SA 4.0：仅限非商业使用；使用时署名并引用来源文献。\n\n<!-- facts:start -->\n'
  + '- 来源：[[sources/figureya|FigureYa 来源库]] · 条目 `FigureYa59volcanoV2`\n- 最近运行：pass（as-is）\n<!-- facts:end -->\n\n'
  + '## 用途\n\n画差异表达火山图。\n\n## 适用\n\n两组比较。\n\n## 不适用\n\n多组。\n\n## 输入\n\n- `easy_input.csv`\n\n'
  + '## 怎么用\n\n- `wiki.py run r-confirm`\n\n## 输出\n\n- `volcano.pdf`\n\n## 知识关联检查\n\n已查。\n\n## 使用记录\n\n<!-- user:start -->\nAuthor note.\n<!-- user:end -->\n';

async function main() {
  const calls: { url: string; init?: RequestInit }[] = [];
  globalThis.fetch = (async (url: string, init?: RequestInit) => {
    calls.push({ url, init });
    if (url === '/api/pages') return { ok: true, json: async () => pages };
    if (url.endsWith('/r-work/confirm')) {
      return { ok: false, statusText: 'Internal Server Error', json: async () => ({ detail: '入库验收未通过：缺少当前原字节的运行收据，请 run' }) };
    }
    return { ok: true, json: async () => detail(confirmable, RECIPE_BODY) };
  }) as any;
  await api.pages();

  await check('new page types have labels, colours, shapes and item wiring', () => {
    for (const type of ['recipe', 'source', 'scenario'] as const) {
      assert.ok(TYPE_LABEL[type], type);
      assert.ok(TYPE_COLOR[type], type);
      assert.equal(typeof TYPE_SHAPE[type], 'number', type);
    }
    assert.equal(TYPE_LABEL.recipe, '配方');
    assert.equal(TYPE_LABEL.source, '来源库');
    assert.equal(TYPE_LABEL.scenario, '研究场景');
    assert.ok(HAS_STATUS('recipe'));
    assert.ok(!HAS_STATUS('source') && !HAS_STATUS('scenario'));
    assert.equal(KIND_OF.recipe, 'recipes');
    assert.ok(isItem(confirmable.meta as any));
    assert.ok(!isItem(source.meta as any) && !isItem(scenario.meta as any));
    const meta = confirmable.meta as any;
    assert.equal(effectiveStatus(meta, flow('recipe_confirm', 'confirm', '') as any), 'draft');
    assert.equal(effectiveStatus(meta, flow('recipe_work', 'agent', '') as any), 'pending_template');
    assert.equal(effectiveStatus(meta, flow('complete', null, '') as any), 'ready');
    assert.ok(STATUS_LABEL[effectiveStatus(meta)]);
  });

  await check('licence badge reads non-commercial only for an NC token', () => {
    assert.ok(isNonCommercial('CC-BY-NC-SA-4.0'));
    assert.ok(isNonCommercial('CC-BY-NC-4.0'));
    assert.ok(!isNonCommercial('NCSA'), 'NCSA is a permissive licence');
    assert.ok(!isNonCommercial('MIT'));
    assert.ok(!isNonCommercial(undefined));
    assert.equal(licenseLabel('CC-BY-NC-ND-4.0'), '非商业');
    assert.equal(licenseLabel('none'), '无许可证');
    assert.equal(licenseLabel('GPL-3.0'), 'GPL-3.0');
  });

  await check('recipe list shows run image or its absence, workflow label, licence and source item', () => {
    const html = renderToStaticMarkup(<RecipesView data={dataOf(pages)} />);
    assert.equal((html.match(/class="plate-card"/g) || []).length, 2, 'archived recipe stays out of the list');
    assert.ok(html.includes('src="/files/wiki/recipes/r-confirm/preview.png"'));
    assert.ok(html.includes('暂无运行图'));
    assert.ok(html.includes('待你确认') && html.includes('待装包'));
    assert.match(html, /class="license-badge nc"[^>]*>非商业</);
    assert.match(html, /class="license-badge"[^>]*>MIT</);
    assert.ok(html.includes('来源：FigureYa 来源库 · FigureYa59r-confirm'));
    assert.ok(html.includes('href="#/page/recipes/r-confirm.md"'));
    assert.ok(!html.includes('查看代码'), 'code endpoints do not serve recipes');
    assert.ok(!html.includes('r-old'));
  });

  await check('confirmable recipe detail renders the body with favourite, archive and confirm', () => {
    const page = detail(confirmable, RECIPE_BODY);
    pageCache.set(page.path, page);
    const html = renderToStaticMarkup(<PageView path={page.path} data={dataOf(pages)} />);
    assert.ok(html.includes('<blockquote>') && html.includes('仅限非商业使用'));
    for (const heading of ['用途', '适用', '不适用', '输入', '怎么用', '输出', '知识关联检查']) assert.ok(html.includes(`<h2>${heading}</h2>`), heading);
    assert.ok(html.includes('最近运行：pass'));
    assert.ok(html.includes('href="#/page/sources/figureya.md"'), 'facts link to the source library');
    assert.ok(html.includes('☆ 收藏') && html.includes('>归档<'));
    assert.ok(html.includes('>确认<'));
    assert.ok(html.includes('href="#/recipes"'), 'breadcrumb returns to the recipe list');
    assert.ok(html.includes('Author note.'), 'note editor keeps the user block');
    assert.ok(!html.includes('查看代码'));
    assert.ok(!html.includes('方法与图的语义关系'), 'recipes have no figure relations section');
  });

  await check('a recipe waiting on the agent has no confirm button; an archived one can be restored, not deleted', () => {
    const work = detail(waiting, RECIPE_BODY);
    pageCache.set(work.path, work);
    const html = renderToStaticMarkup(<PageView path={work.path} data={dataOf(pages)} />);
    assert.ok(!html.includes('>确认<'));
    assert.ok(html.includes('装包须作者按批次批准一次'), 'the backend reason is shown');
    const old = detail(shelved, RECIPE_BODY);
    pageCache.set(old.path, old);
    const archived = renderToStaticMarkup(<PageView path={old.path} data={dataOf(pages)} />);
    assert.ok(archived.includes('>恢复<'));
    assert.ok(!archived.includes('>确认<'));
    assert.ok(!archived.includes('>删除<'), 'backend deletion does not cover recipes');
  });

  await check('confirm posts to the recipe endpoint and surfaces the backend refusal', async () => {
    calls.length = 0;
    await api.confirmRecipe('r-confirm');
    assert.equal(calls[0].url, '/api/recipes/r-confirm/confirm');
    assert.equal(calls[0].init?.method, 'POST');
    await assert.rejects(() => api.confirmRecipe('r-work'), /缺少当前原字节的运行收据/);
  });

  await check('scenario facts table keeps wikilink aliases inside their cells', () => {
    const body = '# 差异表达可视化\n\n<!-- facts:start -->\n\n| 条目 | 级别 | 状态 | 说明 |\n|---|---|---|---|\n'
      + '| [[recipes/r-confirm|火山图配方 r-confirm]] | L1 | draft · 运行 pass | 首选 |\n'
      + '| `figureya:FigureYa59volcanoV2` | L0 | catalog | 目录项 |\n<!-- facts:end -->\n\n## 什么时候用\n\n两组比较。\n\n<!-- user:start -->\n<!-- user:end -->\n';
    const page = detail(scenario, body);
    pageCache.set(page.path, page);
    const html = renderToStaticMarkup(<PageView path={page.path} data={dataOf(pages)} />);
    assert.ok(html.includes('<table>'));
    assert.ok(html.includes('<td><a class="wikilink" href="#/page/recipes/r-confirm.md">火山图配方 r-confirm</a></td>'));
    assert.ok(!html.includes('[['), 'no half wikilink leaks into a cell');
    const rows = html.match(/<tr>[\s\S]*?<\/tr>/g) || [];
    assert.equal(rows.length, 3);
    for (const row of rows) assert.equal((row.match(/<t[hd]>/g) || []).length, 4, row);
    assert.ok(html.includes('href="#/scenarios"'));
  });

  await check('table escaping leaves code fences and non-table lines alone', () => {
    const src = '[[a|b]]\n```\n| [[x|y]] |\n```\n| [[c|d]] | [[e\\|f]] |';
    assert.equal(escapeTableWikilinks(src), '[[a|b]]\n```\n| [[x|y]] |\n```\n| [[c\\|d]] | [[e\\|f]] |');
    const html = renderBody('# T\n\nObsidian [[recipes/r-confirm\\|别名]] link\n', { titles: new Map() });
    assert.ok(html.includes('href="#/page/recipes/r-confirm.md"') && html.includes('>别名<'));
  });

  await check('source page opens without item actions', () => {
    const page = detail(source, '# FigureYa 来源库\n\n<!-- facts:start -->\n- 上游：https://github.com/ying-ge/FigureYa\n<!-- facts:end -->\n\n## 这是什么\n\n上游库。\n\n<!-- user:start -->\n<!-- user:end -->\n');
    pageCache.set(page.path, page);
    const html = renderToStaticMarkup(<PageView path={page.path} data={dataOf(pages)} />);
    assert.ok(html.includes('<h1>FigureYa 来源库</h1>'));
    assert.ok(html.includes('/ 来源库'));
    assert.ok(html.includes('反向链接'));
    assert.ok(!html.includes('收藏'));
  });

  await check('scenario list resolves picks to pages, catalog items and missing ids', () => {
    const picks = (scenario.meta.picks as any[]).map((pick) => resolvePick(pick, pages as any));
    assert.deepEqual(picks.map((p) => p.path), ['recipes/r-confirm.md', 'templates/t-v2.md', null, null]);
    assert.deepEqual(picks.map((p) => p.catalog), [false, false, true, false]);
    const html = renderToStaticMarkup(<ScenariosView data={dataOf(pages)} />);
    assert.ok(html.includes('href="#/page/scenarios/de.md"'));
    assert.ok(html.includes('href="#/page/recipes/r-confirm.md"') && html.includes('href="#/page/templates/t-v2.md"'));
    assert.ok(html.includes('<code>figureya:FigureYa59volcanoV2</code>'));
    assert.ok(html.includes('methods/missing') && html.includes('（页面不存在）'));
    assert.equal(recipeOrigin(confirmable.meta as any, new Map()), 'figureya · FigureYa59r-confirm');
  });

  await check('v2 template without layouts and with no panels is shown with its recipe provenance', () => {
    assert.equal(templateSourceNote(v2template.meta as any, pages as any), '来源：已收录配方');
    assert.equal(templateSourceNote({ ...v2template.meta, sources: undefined } as any, pages as any), '来源记录待核查');
    const entries = galleryEntries(pages as any);
    assert.equal(entries.template.length, 1);
    const html = renderToStaticMarkup(<Gallery data={dataOf(pages)} />);
    assert.ok(html.includes('派生火山图模板'));
    assert.ok(html.includes('来源：已收录配方'));
    assert.ok(!html.includes('原图面板'), 'no empty source panel list');
    const page = detail(v2template, '# 派生火山图模板\n\n## 适用\n\n说明\n\n<!-- user:start -->\n<!-- user:end -->\n');
    pageCache.set(page.path, page);
    const view = renderToStaticMarkup(<PageView path={page.path} data={dataOf(pages)} />);
    assert.ok(view.includes('来源：已收录配方'));
  });

  await check('playbooks, studio, projects and studio-entry buttons render cleanly', () => {
    const methodWithNext = {
      path: 'methods/cell-type-annotation.md',
      meta: {
        type: 'method', id: 'cell-type-annotation', title: '细胞类型注释', method_kind: 'analysis',
        status: 'ready', tags: ['单细胞分析'], favorite: false, inputs: [], outputs: ['scrna-annotated-cells'],
        source: { kind: 'written' }, license: 'none', cite: [],
        next_steps: [{
          direction: '细胞组成比例与组织偏好',
          when: '完成主群注释后检查组间比例变化',
          analysis_templates: ['cell-proportion-stats'],
          intermediate_interface: 'cell-proportion-stats',
          viz_templates: ['t-v2'],
        }],
      },
      implementation_status: [],
    };
    const pbHtml = renderToStaticMarkup(<PlaybooksView data={dataOf([...pages, methodWithNext])} />);
    assert.ok(pbHtml.includes('多路决策沙盘'));
    assert.ok(pbHtml.includes('单细胞转录组步进决策树'));
    assert.ok(pbHtml.includes('Bulk + 101种机器学习标志物决策树'));
    assert.ok(pbHtml.includes('特定修饰/基因集主题挖掘决策树'));
    assert.ok(pbHtml.includes('单细胞 × Bulk 多组学联合决策树'));
    assert.ok(pbHtml.includes('精选条件分支'));
    assert.ok(pbHtml.includes('object_compatible_candidates'));
    assert.ok(pbHtml.includes('切换任意方法节点'));
    assert.ok(pbHtml.includes('class="dag-canvas"'));

    const techMethod = {
      path: 'methods/seurat-helper.md',
      meta: {
        type: 'method', id: 'seurat-helper', title: 'Seurat 对象工具', method_kind: 'technical',
        status: 'ready', tags: [], favorite: false, inputs: [], outputs: [],
        source: { kind: 'written' }, license: 'none', cite: [],
      },
      implementation_status: [],
    };
    const ifacePage = {
      path: 'interfaces/deg-result-table.md',
      meta: {
        type: 'interface', slug: 'deg-result-table', title: '差异基因结果表',
        columns: { gene: { type: 'str', description: '基因', required: true } },
      },
    };
    const resData = dataOf([...pages, methodWithNext, techMethod, ifacePage]);
    const resTechHtml = renderToStaticMarkup(<ResourcesView data={resData} />);
    assert.ok(resTechHtml.includes('资料与检索中心'));
    assert.ok(resTechHtml.includes('技术与适配代码'));
    assert.ok(resTechHtml.includes('数据接口契约'));
    assert.ok(resTechHtml.includes('完整图库索引'));
    assert.ok(resTechHtml.includes('Seurat 对象工具'));
    const resIfaceHtml = renderToStaticMarkup(<ResourcesView data={resData} query="tab=interfaces" />);
    assert.ok(resIfaceHtml.includes('deg-result-table.csv'));
    const resGalleryHtml = renderToStaticMarkup(<ResourcesView data={resData} query="tab=gallery" />);
    assert.ok(resGalleryHtml.includes('#/gallery'));
    const resSearchHtml = renderToStaticMarkup(<ResourcesView data={resData} query="tab=search" />);
    assert.ok(resSearchHtml.includes('全库搜索'));

    const studioHtml = renderToStaticMarkup(<StudioView data={dataOf([...pages, methodWithNext])} query="id=t-v2" />);
    assert.ok(studioHtml.includes('代码模版操控台'));
    assert.ok(studioHtml.includes('嗅探表头'));
    assert.ok(studioHtml.includes('可视化下拉列映射器'));
    assert.ok(studioHtml.includes('NPG') && studioHtml.includes('Lancet') && studioHtml.includes('NEJM'));
    assert.ok(studioHtml.includes('实时脚本编辑器'));
    assert.ok(studioHtml.includes('一键派发到课题目录'));
    assert.ok(studioHtml.includes('本机试跑并预览'));

    const projPage = {
      path: 'projects/2026-asthma-lactylation-scrna.md',
      meta: { type: 'project', title: '2026 哮喘乳酸化单细胞课题' },
    };
    const projHtml = renderToStaticMarkup(<ProjectsView data={dataOf([...pages, projPage])} />);
    assert.ok(projHtml.includes('课题步进看板'));
    assert.ok(projHtml.includes('2026 哮喘乳酸化单细胞课题'));
    assert.ok(projHtml.includes('追加新步进记录'));

    const recipeListHtml = renderToStaticMarkup(<RecipesView data={dataOf(pages)} />);
    assert.ok(recipeListHtml.includes('#/studio?id=r-confirm'), 'recipe card links to Studio');
    assert.ok(recipeListHtml.includes('打开工作台'));

    const page = detail(v2template, '# 派生火山图模板\n\n<!-- user:start -->\n<!-- user:end -->\n');
    pageCache.set(page.path, page);
    const detailHtml = renderToStaticMarkup(<PageView path={page.path} data={dataOf(pages)} />);
    assert.ok(detailHtml.includes('#/studio?id=t-v2'), 'template detail page links to Studio');
  });

  if (failed) process.exitCode = 1;
  else console.log('v2 page types: all checks passed');
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
