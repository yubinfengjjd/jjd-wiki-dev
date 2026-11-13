import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '..');
async function sourceFiles(dir) { const entries=await fs.readdir(dir,{withFileTypes:true}); return (await Promise.all(entries.map(entry=>entry.isDirectory()?sourceFiles(path.join(dir,entry.name)):[path.join(dir,entry.name)]))).flat(); }
test('runtime source has no persistence, networking, upstream examples or host filesystem access', async () => {
  for (const file of await sourceFiles(path.join(root,'src'))) {
    if (file.endsWith('.css')) continue;
    const source=await fs.readFile(file,'utf8');
    for (const forbidden of [/localStorage\s*\./,/sessionStorage\s*\./,/\bfetch\s*\(/,/XMLHttpRequest/,/WebSocket/,/node:fs/,/from ['"]fs['"]/,/vault\.(?:create|modify|delete|rename|process|append)\s*\(/,/adapter\.(?:write|remove|mkdir|rename)\s*\(/,/processFrontMatter\s*\(/,/saveData\s*\(/,/data\/sample/,/seedIdeas|seedDrafts/]) assert.doesNotMatch(source,forbidden,file);
  }
});
test('original moving media are intact and native plugin id matches install directory', async () => {
  const manifest=JSON.parse(await fs.readFile(path.join(root,'manifest.json'),'utf8'));
  assert.equal(manifest.id,'research-wiki-neural-view');
  for (const name of ['orb.mp4','orb.jpg','jellyfish.mp4','jellyfish.jpg']) {
    const local=await fs.readFile(path.join(root,'media',name));
    const original=await fs.readFile(path.join(root,'upstream/public/media',name));
    assert.ok(local.length>1000); assert.ok(local.equals(original),name);
  }
});
