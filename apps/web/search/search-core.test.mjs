// node --test frontend/search/search-core.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { filter, facetCounts, encodeState, decodeState, pageHref, sourceHref } from './search-core.js';

const entries = [
  { id: 'a', kind: 'recipe', charts: ['heatmap'], domains: ['single-cell'], packages: ['pheatmap'], _text: 'a 热图 single-cell pheatmap' },
  { id: 'b', kind: 'recipe', charts: ['bar'], domains: ['single-cell', 'transcriptomics'], packages: ['ggplot2'], _text: 'b bar ggplot2' },
  { id: 'c', kind: 'template', charts: [], domains: [], packages: [], _text: 'c shap' },
];
const empty = { q: '', kind: '', charts: [], domains: [], packages: [] };

test('OR within a facet, AND across facets and query', () => {
  assert.deepEqual(filter(entries, { ...empty, charts: ['heatmap', 'bar'] }).map((e) => e.id), ['a', 'b']);
  assert.deepEqual(filter(entries, { ...empty, charts: ['heatmap', 'bar'], packages: ['ggplot2'] }).map((e) => e.id), ['b']);
  assert.deepEqual(filter(entries, { ...empty, q: 'SHAP' }).map((e) => e.id), ['c']);
  assert.deepEqual(filter(entries, { ...empty, kind: 'recipe', q: 'single-cell 热图' }).map((e) => e.id), ['a']);
});

test('facet counts ignore their own selection', () => {
  const counts = facetCounts(entries, { ...empty, domains: ['transcriptomics'] }, 'domains');
  assert.equal(counts.get('single-cell'), 2);
  assert.equal(facetCounts(entries, { ...empty, domains: ['transcriptomics'] }, 'charts').get('heatmap'), undefined);
});

test('state round-trips through the hash; links encode path segments', () => {
  const state = { q: '单细胞 umap', kind: 'recipe', charts: ['heatmap'], domains: [], packages: ['Seurat', 'ggplot2'] };
  assert.deepEqual(decodeState('#' + encodeState(state)), state);
  assert.equal(pageHref('/', 'recipes/x y.md'), '/#/page/recipes/x%20y.md');
  assert.equal(pageHref('/', ''), '');
});

test('rejects executable app and source protocols', () => {
  for (const base of ['javascript:alert(1)//', 'data:text/html,<svg>', ' java\tscript:alert(1)//']) {
    assert.equal(pageHref(base, 'recipes/x.md'), '');
    assert.equal(sourceHref(base, 'recipes/x.md'), '');
  }
});

test('standalone results use encoded web source links without an app', () => {
  assert.equal(pageHref('', 'recipes/x y.md'), '');
  assert.equal(sourceHref('https://github.com/test/wiki/blob/main/', 'recipes/x y.md'),
    'https://github.com/test/wiki/blob/main/recipes/x%20y.md');
  assert.equal(pageHref('http://127.0.0.1:8765/', 'recipes/x.md'),
    'http://127.0.0.1:8765/#/page/recipes/x.md');
});

test('canonical source link and complete full-text kind filters', async () => {
  const {DEFAULT_SOURCE_BASE, kindOptions} = await import('./search-core.js');
  assert.equal(sourceHref(DEFAULT_SOURCE_BASE, 'interfaces/units.md'),
    'https://github.com/yubinfengjjd/jjd-wiki/blob/main/wiki/interfaces/units.md');
  const legacy = {facets: {kinds: [{value: 'method', count: 1}]}};
  const full = {documents: ['method', 'interface', 'chart-type', 'project', 'layout', 'source']
    .map(kind => ({record: {kind}}))};
  assert.equal(kindOptions(legacy, full, 'facets').length, 1);
  assert.deepEqual(new Set(kindOptions(legacy, full, 'full').map(k => k.value)),
    new Set(['method', 'interface', 'chart-type', 'project', 'layout', 'source']));
});
