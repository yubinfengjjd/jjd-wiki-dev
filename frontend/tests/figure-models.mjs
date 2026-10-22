import {createRequire} from 'node:module';
import {mkdtemp, readFile, unlink, rmdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const root=resolve(fileURLToPath(new URL('..',import.meta.url)));
const require=createRequire(join(root,'package.json'));
const {build}=require('esbuild');
const dir=await mkdtemp(join(tmpdir(),'rwiki-figures-'));
const outfile=join(dir,'test.cjs');
try {
await build({stdin:{contents:`
import assert from 'node:assert/strict';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {galleryEntries,methodDisplayFigures,singlePanelKnowledge} from './src/figureModels';
import {RelationList} from './src/RelationList';
import {adaptableTemplateRelations} from './src/relations';
import {Chain} from './src/views/Chain';
import {Gallery} from './src/views/Gallery';
import {Flow} from './src/flow';
import {api} from './src/api';
const source=(id,tid='shared')=>({path:'layouts/'+id+'.md',meta:{type:'layout',id,title:id,status:'pending_template',
 language:'python',tags:[],favorite:false,panels:{A:'bar'},chart_types:['bar'],templates:[tid],template_panels:{[tid]:['A']}},
 workflow:{stage:'complete',queue:null,label:'模板已就绪',templates:[]}});
const template=(id,layouts=['one','two'])=>({path:'templates/'+id+'.md',meta:{type:'template',id,title:id,status:'ready',
 language:'python',tags:[],favorite:false,panels:['A'],chart_types:['bar'],layouts},
 workflow:{stage:'complete',queue:null,label:'可用',templates:[]}});
const items=[source('one'),source('two'),template('shared')];
const before=JSON.stringify(items);
let shown=galleryEntries(items);
assert.equal(shown.single.length,1);
assert.equal(shown.template.length,1);
assert.equal(shown.single[0].sourceLinks.length,2);
assert.equal(methodDisplayFigures(items.map(p=>({...p,relation:'reference'})))[0].sourceLinks.length,2);
assert.equal(JSON.stringify(items),before);
const unknown=structuredClone(items); unknown[0].meta.template_panels={};
assert.equal(galleryEntries(unknown).single.length,2);
const distinct=[source('one','style-a'),source('two','style-b'),template('style-a',['one']),template('style-b',['two'])];
assert.equal(galleryEntries(distinct).single.length,2);
assert.equal(galleryEntries(distinct).template.length,2);
const history=source('whole');history.meta.panels={A:'bar',B:'beeswarm'};history.meta.status='archived';
const raw=[...items,history,...['SHAP 条形图','SHAP 蜂群图','SHAP 环形图'].map(id=>template(id,['whole']))];
const graph={nodes:[],links:[]};const visible=singlePanelKnowledge(raw,graph);
assert.equal(galleryEntries(visible.pages).single.length,4);
assert.equal(galleryEntries(visible.pages).template.length,4);
async function main(){
 globalThis.fetch=async()=>({ok:true,json:async()=>visible.pages});await api.pages();
 const html=renderToStaticMarkup(<Gallery data={{pages:visible.pages,graph,flow:new Flow(graph),
  env:{titles:new Map(),hiddenSources:visible.hiddenSources},reload:async()=>{}}}/>);
 assert.equal((html.match(/class="plate-card"/g)||[]).length,4);
 for(const title of ['SHAP 条形图','SHAP 蜂群图','SHAP 环形图'])assert.ok(html.includes(title));
 assert.ok(html.includes('href="#/page/layouts/one.md"')&&html.includes('href="#/page/layouts/two.md"'));
 const layoutRelation={method:'methods/m.md',figure:'layouts/one.md',method_title:'Method',figure_title:'Layout one',
  method_status:'ready',figure_status:'pending_template',compatibility:'adaptable',reason:'reason',
  prerequisites:[],adaptation:'adapt',evidence:[],verification:{state:'not_run',scope:'scope'},
  target_kind:'layout',active:true};
 const relationHtml=renderToStaticMarkup(<RelationList relations={[layoutRelation]} self="layouts/one.md" pages={items}/>);
 assert.ok(relationHtml.includes('模板已就绪'));
 assert.ok(!relationHtml.includes('待模板化'));
 const templateRelation={...layoutRelation,figure:'templates/shared.md',figure_title:'Template',
  target_kind:'template',figure_status:'ready'};
 assert.equal(adaptableTemplateRelations([layoutRelation,templateRelation]).length,1);
 const methodPage={path:'methods/m.md',meta:{type:'method',id:'m',title:'Method',status:'ready',tags:[],
  favorite:false,inputs:[],outputs:[],source:{kind:'written'},license:'none',cite:[]}};
 const chainHtml=renderToStaticMarkup(<Chain title="接口结构匹配" hint="hint" self="methods/m.md"
  columns={[{label:'分析方法',pages:[methodPage]},{label:'结构匹配的模板',pages:[items[2]]}]}
  detailOf={(p)=>p.startsWith('templates/')?'读取：Example interface':''}/>);
 assert.ok(chainHtml.includes('读取：Example interface'));
 assert.ok(chainHtml.includes('chain-detail'));
 console.log('figure models and Gallery SSR: 20 checks passed');
}
main().catch(e=>{console.error(e);process.exit(1)});
`,resolveDir:root,loader:'tsx'},outfile,bundle:true,platform:'node',format:'cjs',jsx:'automatic',target:'node22',logLevel:'silent'});
const result=spawnSync(process.execPath,[outfile],{encoding:'utf8'});
process.stdout.write(result.stdout);process.stderr.write(result.stderr);
if(result.status)process.exitCode=result.status;
} finally { await unlink(outfile).catch(()=>{});await rmdir(dir); }
