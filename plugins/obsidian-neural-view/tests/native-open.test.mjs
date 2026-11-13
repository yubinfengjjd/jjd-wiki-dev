import test from 'node:test';
import assert from 'node:assert/strict';
import {openExistingNote} from '../src/native-open.mjs';
class File { constructor(path) {this.path=path;this.extension=path.split('.').at(-1);} }
function app(current) {
  const opened=[];
  return {opened,vault:{getAbstractFileByPath:()=>current},workspace:{getLeaf:kind=>{assert.equal(kind,'tab');return {openFile:async file=>{opened.push(file);}};}}};
}
test('only an existing exact formal markdown TFile opens natively', async () => {
  const file=new File('methods/a.md'), api=app(file);
  assert.equal(await openExistingNote(api,'methods/a.md',f=>f instanceof File),true);
  assert.deepEqual(api.opened,[file]);
});
test('stale deleted or renamed graph nodes never create or open phantom notes', async () => {
  for(const current of [null,new File('methods/renamed.md'),{path:'methods/a.md',extension:'md'},new File('methods/a.txt')]) {
    const api=app(current);
    assert.equal(await openExistingNote(api,'methods/a.md',f=>f instanceof File),false);
    assert.deepEqual(api.opened,[]);
  }
});
test('excluded resources cannot be opened through graph action even if present', async () => {
  for(const path of ['methods/a/source/README.md','.obsidian/cache.md','chart-types/a.md']) {
    const api=app(new File(path));
    assert.equal(await openExistingNote(api,path,f=>f instanceof File),false);
    assert.deepEqual(api.opened,[]);
  }
});
