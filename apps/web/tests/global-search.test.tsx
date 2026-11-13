import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import * as search from '../src/search';
import * as view from '../src/views/SearchView';
import { parseRoute } from '../src/route';
import {effectiveStatus} from '../src/api';

async function main() {
  assert.equal(typeof search.latestSearch, 'function', 'search must protect against late responses');
  let finishOld!: (value: string) => void;
  const old = new Promise<string>(resolve => { finishOld = resolve; });
  const values: string[] = [];
  const signals: AbortSignal[] = [];
  const run = search.latestSearch<string>();
  const pending = run(signal => { signals.push(signal); return old; }, value => values.push(value), () => {});
  await run(async () => 'new', value => values.push(value), () => {});
  assert.equal(signals[0].aborted, true);
  finishOld('old'); await pending;
  assert.deepEqual(values, ['new'], 'an out-of-order success must not replace the current query');
  let rejectOld!: (error: Error) => void;
  const rejected = new Promise<string>((_, reject) => { rejectOld = reject; });
  const errors: string[] = [];
  const failing = run(() => rejected, value => values.push(value), error => errors.push(error.message));
  await run(async () => 'newest', value => values.push(value), error => errors.push(error.message));
  rejectOld(new Error('old error')); await failing;
  assert.deepEqual(errors, [], 'a superseded error must not erase a current result');
  run.cancel();
  const selection = search.parseSearchQuery('q=R%26D+%E5%B7%AE%E5%BC%82&kind=method&scope=source&runnable=true');
  assert.equal(selection.q, 'R&D 差异');
  assert.deepEqual(search.parseSearchQuery(search.searchHref(selection).split('?')[1]), selection);
  const href = search.searchResultHref({ page: 'methods/a b.md', match_section: '用途 & 前提' } as any);
  assert.equal(parseRoute(href).query, 'section=%E7%94%A8%E9%80%94+%26+%E5%89%8D%E6%8F%90');
  assert.deepEqual(search.sectionTargets('用途'), ['用途', '研究问题与用途']);
  const result: any = {id: 'x', title: '<script>alert(1)</script>', kind: 'method', page: 'methods/x.md', summary: '',
    snippet: '<img src=x onerror=alert(1)>', match_section: '前提', why: ['正文命中'], usable: false,
    asset_availability: 'not_downloaded', evidence_state: 'not_run', run: 'none'};
  const html = renderToStaticMarkup(<view.SearchResults results={[result]} onDownload={() => {}} downloading="" />);
  assert.ok(html.includes('&lt;script&gt;') && html.includes('&lt;img'));
  assert.ok(!html.includes('<script>') && !html.includes('<img'));
  assert.ok(html.includes('下载资料') && html.includes('未下载'));
  const available = renderToStaticMarkup(<view.SearchResults results={[{...result, asset_availability: 'available'}]} onDownload={() => {}} downloading="" />);
  assert.ok(!available.includes('下载资料'), 'only not_downloaded assets have the fetch action');
  const item = renderToStaticMarkup(<view.SearchResults results={[{...result, id: 'figureya:Module1', kind: 'item',
    use: 'wiki.py use figureya:Module1 --project <课题目录>'}]} onDownload={() => {}} downloading="" />);
  assert.ok(!item.includes('下载资料') && item.includes('rwiki use figureya:Module1'),
    'L0 sources must use the upstream-aware reuse entry rather than the page-asset endpoint');
  const source = renderToStaticMarkup(<view.SearchResults results={[{...result, source_scope: true, source_path: 'methods/x/source/main.R', evidence_state: 'unknown'}]} onDownload={() => {}} downloading="" />);
  assert.ok(source.includes('来源文件') && source.includes('methods/x/source/main.R'));
  assert.ok(source.includes('尚未核对') && !source.includes('运行证据：unknown'));
  assert.equal(effectiveStatus({type: 'template', status: 'ready'} as any,
    {stage: 'unknown', queue: null, label: '尚未核对', reason: '', templates: []}), 'pending_template');
  console.log('global search: latest requests, escaped text, filters and section links passed');
}
main().catch(error => {console.error(error); process.exit(1);});
