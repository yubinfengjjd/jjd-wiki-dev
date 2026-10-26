import test from 'node:test';
import assert from 'node:assert/strict';
import {categoryOf, parseWikiLinks, fallbackResolve, readGraph} from '../src/adapter.mjs';

function fixture(contents, frontmatter = {}) {
  const files = Object.keys(contents).map(path => ({path, basename: path.split('/').at(-1).replace(/\.md$/, '')}));
  const reads = [];
  const vault = {getMarkdownFiles: () => files, cachedRead: async file => {reads.push(file.path); return contents[file.path];}, getAbstractFileByPath: path => path === 'layouts/a/thumb.png' ? {path} : null, adapter: {getResourcePath: path => `app://fixture/${path}`}};
  const metadata = {getFileCache: file => frontmatter[file.path] ? {frontmatter: frontmatter[file.path], links: parseWikiLinks(contents[file.path])} : null, getFirstLinkpathDest: (link, source) => fallbackResolve(link, source, files)};
  return {vault, metadata, reads, files};
}
test('entry boundary excludes root admin, nested evidence, cache and unsupported folders', () => {
  for (const path of ['layouts/AGENTS.md','methods/README.md','projects/index.md','interfaces/changelog.md','templates/a/verify/report.md','methods/a/source/README.md','.obsidian/cache.md','chart-types/bar.md','projects/verify/report.md','log.md','templates-old/a.md']) assert.equal(categoryOf(path), null, path);
  for (const category of ['layouts','templates','methods','interfaces','projects']) assert.equal(categoryOf(`${category}/a.md`), category);
});
test('qualified wikilinks, aliases, headings, relative targets and ambiguous basenames', () => {
  const {files} = fixture({'layouts/a.md':'','methods/a.md':'','templates/b.md':'','methods/汉字.md':''});
  assert.equal(fallbackResolve('methods/a#Section|alias','layouts/a.md',files)?.path, 'methods/a.md');
  assert.equal(fallbackResolve('../methods/a','layouts/a.md',files)?.path, 'methods/a.md');
  assert.equal(fallbackResolve('methods/%E6%B1%89%E5%AD%97','layouts/a.md',files)?.path, 'methods/汉字.md');
  assert.equal(fallbackResolve('wrong/a','templates/b.md',files), null);
  assert.equal(fallbackResolve('a','templates/b.md',files), null);
  assert.equal(fallbackResolve('https://x/a','templates/b.md',files), null);
  assert.equal(fallbackResolve('#local','templates/b.md',files)?.path, 'templates/b.md');
});
test('fallback ignores frontmatter, comments and code while preserving aliases and image embeds', () => {
  assert.deepEqual(parseWikiLinks('---\ntitle: "[[no]]"\n---\n```md\n[[no2]]\n```\n`[[no3]]`\n<!-- [[no4]] -->\n[[methods/a#H|Alias]] ![[a.png]]'), [{link:'methods/a#H',displayText:'Alias',embed:false},{link:'a.png',displayText:'',embed:true}]);
});
test('real references only; raw status is preserved and tags/prose never invent compatibility', async () => {
  const f = fixture({
    'layouts/a.md':'[[templates/b|B]]\n[[methods/missing|Missing]]\n[[chart-types/bar|Chart]]\nText recommends templates/c and SHAP #shared',
    'templates/b.md':'[[layouts/a]]',
    'templates/c.md':'SHAP #shared',
    'methods/d.md':'No links',
    'chart-types/bar.md':'Excluded',
    'templates/a/verify/report.md':'Excluded',
    'methods/AGENTS.md':'Excluded'
  }, {'layouts/a.md':{title:'Original title',status:'pending_template',tags:['shared']}});
  const graph = await readGraph(f.vault,f.metadata);
  assert.equal(graph.nodes.length, 4);
  assert.equal(graph.index.get('layouts/a.md').title, 'Original title');
  assert.equal(graph.index.get('layouts/a.md').rawStatus, 'pending_template');
  assert.equal(graph.index.get('layouts/a.md').status, undefined);
  assert.equal(graph.links.length, 1);
  assert.equal(graph.links[0].both, true);
  assert.equal(graph.links[0].kind, 'wiki');
  assert.equal(graph.unresolved, 1);
  assert.equal(graph.index.get('layouts/a.md').thumbnail, 'app://fixture/layouts/a/thumb.png');
  assert.equal(graph.index.get('layouts/a.md').references[0].label, 'B');
  assert.equal(graph.index.get('layouts/a.md').references[1].resolved, false);
  assert.equal(graph.index.get('layouts/a.md').references[2].excluded, true);
  assert.deepEqual(f.reads.sort(), ['layouts/a.md','methods/d.md','templates/b.md','templates/c.md']);
  assert.equal(graph.index.get('templates/c.md').deg, 0);
});
test('Obsidian cache resolver is authoritative; adapter does not second guess ambiguous destinations', async () => {
  const f = fixture({'layouts/a.md':'[[methods/b|B]]','methods/b.md':'','templates/b.md':''});
  const calls=[];
  f.metadata.getFirstLinkpathDest=(link,source)=>{calls.push([link,source]); return null;};
  const graph = await readGraph(f.vault,f.metadata);
  assert.deepEqual(calls,[['methods/b','layouts/a.md']]);
  assert.equal(graph.links.length,0);
  assert.equal(graph.unresolved,1);
});
test('empty vault has no samples or synthetic module nodes', async () => {
  const f=fixture({}); const graph=await readGraph(f.vault,f.metadata);
  assert.deepEqual(graph.nodes,[]); assert.deepEqual(graph.links,[]); assert.equal(graph.unresolved,0);
});
