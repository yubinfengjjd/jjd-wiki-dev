// node --test frontend/search/search-core.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { filter, facetCounts, encodeState, decodeState, pageHref } from './search-core.js';

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
