import test from 'node:test';
import assert from 'node:assert/strict';
import * as full from './full-search.js';

test('ranked full-text search uses section relevance, exact filters and stable ties', () => {
  assert.equal(typeof full.rankExport, 'function');
  const index = {tokenizer: {aliases: [['差异表达', 'DEG']], cjk_ngrams: [2]}, ranking: {k1: 1.2, b: .75},
    statistics: {document_count: 3, average_length: 2, df: {gene: 3, '@0': 1}}, documents: [
      {record: {id: 'weak', kind: 'method', scope: 'knowledge', usable: true}, sections: [{title: '背景', text: 'gene', length: 8, tf: {gene: 1}}]},
      {record: {id: 'strong', kind: 'method', scope: 'knowledge', usable: false}, sections: [{title: '前提', text: 'gene DEG', length: 2, tf: {gene: 4, '@0': 1}}]},
    ]};
  assert.deepEqual(full.rankExport(index, 'gene').map(x => x.id), ['strong', 'weak']);
  assert.deepEqual(full.rankExport(index, 'gene', {runnable: true}).map(x => x.id), ['weak']);
  assert.deepEqual(full.rankExport(index, 'gene', {scope: 'source'}), []);
  assert.deepEqual(full.rankExport({...index, coverage: {scope: 'source'}}, 'gene', {scope: 'source'}).map(x => x.id), ['strong', 'weak']);
  assert.deepEqual(full.rankExport(index, '差异表达').map(x => x.id), ['strong']);
  assert.deepEqual(full.rankExport(index, 'gene', {kind: 'template'}), []);
  assert.deepEqual(full.rankExport(index, '  '), []);
  assert.equal(full.rankExport(index, 'gene')[0].match_section, '前提');
});

test('query normalization honors case, CJK bigrams and bounded English aliases', () => {
  assert.deepEqual([...full.queryTokens('GeNe 差异表达', {aliases: [['差异表达', 'DEG']]})].sort(), ['@0', 'gene', '差异', '异表', '表达'].sort());
  assert.ok(!full.queryTokens('degree', {aliases: [['差异表达', 'DEG']]}).has('@0'));
  assert.deepEqual([...full.queryTokens('判断每个细胞属于什么类型', {stopwords: ['每个', '属于', '判断', '什么']})], ['细胞', '胞类', '类型']);
});


test('exact phrases reward order and enforce ASCII word boundaries', () => {
  const index = {tokenizer:{aliases:[]}, ranking:{k1:1.2,b:.75,phrase_weight:.5},
    statistics:{document_count:3,average_length:4,df:{alpha:3,beta:3}},documents:[
      {record:{id:'a-reversed',title:'Order'},sections:[{title:'原理',text:'beta alpha',length:4,tf:{alpha:1,beta:1}}]},
      {record:{id:'z-ordered',title:'Order'},sections:[{title:'原理',text:'alpha beta',length:4,tf:{alpha:1,beta:1}}]},
      {record:{id:'substring',title:'Order'},sections:[{title:'原理',text:'unalpha betaextra alpha separately beta',length:4,tf:{alpha:1,beta:1}}]},
    ]};
  const hits=full.rankExport(index,'"alpha beta"');
  assert.equal(hits[0].id,'z-ordered');
  assert.ok(hits[0].why.some(x=>x.includes('精确短语')));
  assert.ok(!hits.find(x=>x.id==='substring').why.some(x=>x.includes('精确短语')));
});
