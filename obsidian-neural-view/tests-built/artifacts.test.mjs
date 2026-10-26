import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import postcss from 'postcss';
const root = path.resolve(import.meta.dirname, '..');
test('built CSS has no selector or animation leaking into the native note editor', async () => {
  const css=postcss.parse(await fs.readFile(path.join(root,'dist/styles.css'),'utf8'));
  css.walkRules(rule=>{
    if(rule.parent.type==='atrule' && rule.parent.name.endsWith('keyframes')) return;
    for(const selector of rule.selectors) assert.ok(selector.startsWith('.research-neural-view ' ) || selector==='.research-neural-view',selector);
  });
  css.walkAtRules(rule=>{if(rule.name.endsWith('keyframes')) assert.match(rule.params,/^rnv-/);});
  css.walkDecls(decl=>{if(decl.prop==='animation') for(const word of ['breathe','introFade','slideIn','dockIn']) assert.doesNotMatch(decl.value,new RegExp(`(?<![\\w-])${word}(?![\\w-])`));});
});
test('native bundle remains external to Obsidian and excludes preview fixtures/upstream data', async () => {
  const source=await fs.readFile(path.join(root,'dist/main.js'),'utf8');
  assert.match(source,/require\("obsidian"\)/);
  assert.doesNotMatch(source,/fixture-layout|fixture-template|previewUnmount|seedIdeas|seedDrafts|src\/data\/sample/);
  assert.doesNotMatch(source,/localStorage\.(?:setItem|removeItem)|sessionStorage\.(?:setItem|removeItem)/);
});
test('distribution contains exact local moving assets and retained upstream licenses', async () => {
  for(const name of ['orb.mp4','orb.jpg','jellyfish.mp4','jellyfish.jpg']) assert.ok((await fs.readFile(path.join(root,'dist/media',name))).equals(await fs.readFile(path.join(root,'media',name))),name);
  for(const name of ['LICENSE','NOTICE.md']) assert.ok((await fs.readFile(path.join(root,'dist',name))).equals(await fs.readFile(path.join(root,'upstream',name))),name);
});
