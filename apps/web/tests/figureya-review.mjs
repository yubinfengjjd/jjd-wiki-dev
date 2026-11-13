import {createRequire} from 'node:module';
import {mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const root=resolve(fileURLToPath(new URL('..',import.meta.url)));
const require=createRequire(join(root,'package.json'));
const {build}=require('esbuild');
const dir=await mkdtemp(join(tmpdir(),'rwiki-review-'));
try {
  const outfile=join(dir,'test.cjs');
  await build({stdin:{contents:`
import assert from 'node:assert/strict';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {Picture,reviewItems} from './src/views/FigureYaReview';
const make=(source,n)=>({id:source+':FigureYa'+n,source_id:source,title:'样式'+n,decision:'pending',
  summary:'',scenario:'',keywords:[],tags:[],chart_types:['bar'],inputs:[],requires:[],
  page:'sources/'+source+'.md',license:'',use:'rwiki use '+source+':FigureYa'+n,
  thumb:'/api/figureya/image?id='+n,images:[{url:'/api/figureya/image?id='+n}],recipes:[]});
const original=Array.from({length:313},(_,n)=>make('figureya',n+1));
original[0].recipes=[{id:'promoted'}];
const all=[...original,...Array.from({length:33},(_,n)=>make('figureya-archive',n+1))];
assert.equal(reviewItems(all,'figureya','all','','').length,313);
assert.equal(reviewItems(all,'figureya-archive','all','','').length,33);
assert.equal(reviewItems(all,'figureya','all','','')[0].recipes.length,1);
original[0].decision='removed';
assert.equal(reviewItems(all,'figureya','removed','','').length,1);
assert.equal(reviewItems(all,'figureya','pending','','').length,312);
assert.equal(reviewItems(all,'figureya','all','FigureYa313','bar').length,1);
// The review renders real image elements for local preview URLs.
const html=renderToStaticMarkup(<div>{original.slice(0,3).map(item=><Picture key={item.id} item={item} index={0} />)}</div>);
assert.equal((html.match(/<img /g)||[]).length,3);
assert.ok(html.includes('/api/figureya/image'));
console.log('FigureYa review: 313 originals, promoted entries, versions and visual previews passed');
`,resolveDir:root,loader:'tsx'},bundle:true,platform:'node',format:'cjs',outfile,logLevel:'silent'});
  const result=spawnSync(process.execPath,[outfile],{stdio:'inherit'});
  if(result.status!==0) process.exitCode=result.status??1;
} finally {
  if(dirname(resolve(dir))!==resolve(tmpdir())) throw new Error('Unexpected test cleanup path');
  await rm(dir,{recursive:true,force:true});
}
