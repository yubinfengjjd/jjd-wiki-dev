import assert from 'node:assert/strict';
import * as figures from '../src/figureModels';
import * as apiModule from '../src/api';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {CatalogCards, matchesCatalog, SourcesView} from '../src/views/SourcesView';
import {Flow} from '../src/flow';

async function main() {
  assert.equal(typeof figures['matchesFigureQuery'], 'function', 'gallery must support source/id/keyword queries');
  const pages: any[] = [
    {path: 'sources/figureya.md', meta: {type: 'source', id: 'figureya', title: 'FigureYa 医学绘图'}},
    {path: 'recipes/module.md', meta: {type: 'recipe', id: 'module', title: '火山图配方', source: {id: 'figureya', item: 'Module59'}}},
  ];
  const template: any = {type: 'template', id: 'volcano', title: '差异火山图', tags: [], chart_types: ['volcano'],
    sources: ['recipes/module'], keywords: ['limma']};
  assert.equal(figures['matchesFigureQuery'](template, 'FigureYa', pages), true);
  assert.equal(figures['matchesFigureQuery'](template, '医学绘图 limma', pages), true);
  assert.equal(figures['matchesFigureQuery'](template, 'unrelated', pages), false);
  const catalog: any = {id: 'figureya:FigureYa59', title: '火山图', summary: '差异表达', scenario: '',
    tags: [], keywords: ['limma'], chart_types: ['volcano'], inputs: ['result.csv'], requires: ['ggplot2'],
    thumb: 'javascript:alert(1)', license: 'CC-BY-NC-SA-4.0', page: 'sources/figureya.md',
    use: 'wiki.py use figureya:FigureYa59 --project <课题目录>', level: 'L0', usable: false, run: 'none'};
  assert.equal(matchesCatalog(catalog, 'FigureYa limma'), true);
  assert.equal(matchesCatalog(catalog, 'result.csv'), true);
  const cards = renderToStaticMarkup(<CatalogCards items={[catalog]}/>);
  assert.ok(cards.includes('未在 Wiki 运行') && cards.includes('rwiki use'));
  assert.ok(!cards.includes('javascript:') && !cards.includes('可原样运行'));
  const sourceData: any = {pages: [...pages, {path: 'templates/volcano.md', meta: {...template, status: 'ready'}}],
    hiddenPages: [], graph: {nodes: [], links: []}, flow: new Flow({nodes: [], links: []}),
    env: {titles: new Map(), hiddenSources: new Set()}, reload: async () => {}};
  const none = renderToStaticMarkup(<SourcesView data={sourceData} query="q=no-such-module" />);
  assert.ok(!none.includes('火山图配方') && !none.includes('差异火山图'), 'source search must filter L1 and L2 as well as L0');
  const promoted = renderToStaticMarkup(<SourcesView data={sourceData} query="q=Module59" />);
  assert.ok(promoted.includes('火山图配方') && promoted.includes('差异火山图'), 'promoted modules remain discoverable by upstream item');

  assert.equal(apiModule.effectiveStatus({...template, status: 'ready'},
    {stage: 'checking', queue: null, label: '正在核对证据', reason: '', templates: []}), 'pending_template');
  assert.equal(typeof apiModule['loadLibrary'], 'function', 'initial pages must not wait for graph or verification');
  let finishFull: (value: unknown) => void;
  const full = new Promise(resolve => {finishFull = resolve;});
  const seen: string[] = [];
  globalThis.fetch = (async (url: string) => {
    if (url === '/api/pages?light=true') return {ok: true, json: async () => [{path: 'templates/t.md', meta: template}]};
    if (url === '/api/pages') return {ok: true, json: () => full};
    if (url === '/api/graph') return {ok: true, json: async () => ({nodes: [], links: []})};
    return {ok: true, json: async () => ({total: 0, domains: [], purposes: [], unclassified: []})};
  }) as any;
  const loading = apiModule['loadLibrary']({pages: () => seen.push('pages'), graph: () => seen.push('graph'),
    taxonomy: () => seen.push('taxonomy'), error: () => seen.push('error')});
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(seen[0], 'pages', 'the first render must be independent of full evidence checks');
  assert.equal(seen.filter(x => x === 'pages').length, 1);
  finishFull!([]);
  await loading;
  assert.equal(seen.filter(x => x === 'pages').length, 2);
  assert.equal(seen.includes('error'), false);

  let active = true;
  let releaseOld: (value: unknown) => void;
  const oldFull = new Promise(resolve => {releaseOld = resolve;});
  const checking = {stage: 'checking', queue: null, label: '正在核对证据', reason: '', templates: []};
  globalThis.fetch = (async (url: string) => {
    if (url === '/api/pages?light=true') return {ok: true, json: async () => [{path: 'templates/t.md', meta: {...template, status: 'ready'}, workflow: checking}]};
    if (url === '/api/pages') return {ok: true, json: () => oldFull};
    return {ok: true, json: async () => ({nodes: [], links: []})};
  }) as any;
  seen.length = 0;
  const oldLoading = apiModule['loadLibrary']({pages: () => seen.push('pages'), graph: () => {}, taxonomy: () => {}}, () => active);
  await new Promise(resolve => setTimeout(resolve, 0));
  active = false;
  releaseOld!([{path: 'templates/t.md', meta: {...template, status: 'ready'}, workflow: {...checking, stage: 'complete'}}]);
  await oldLoading;
  assert.equal(seen.length, 1);
  assert.equal(apiModule.workflowOf(template)?.stage, 'checking', 'a late full response must not overwrite the current evidence cache');

  globalThis.fetch = (async (url: string) => {
    if (url === '/api/graph') throw new Error('graph unavailable');
    return {ok: true, json: async () => []};
  }) as any;
  seen.length = 0;
  await apiModule['loadLibrary']({pages: () => seen.push('pages'), graph: () => seen.push('graph'),
    taxonomy: () => seen.push('taxonomy'), error: () => seen.push('error')});
  assert.equal(seen.filter(x => x === 'pages').length, 2, 'a graph failure must not remove loaded pages');
  assert.equal(seen.includes('error'), true);

  seen.length = 0;
  await apiModule['loadLibrary']({pages: () => seen.push('pages'), graph: () => seen.push('graph'),
    taxonomy: () => seen.push('taxonomy')}, () => false);
  assert.deepEqual(seen, [], 'superseded loads must never overwrite a newer snapshot');
  console.log('discovery/loading: source search, pending evidence, staged loading and stale-load checks passed');
}
main().catch(error => {console.error(error); process.exit(1);});
