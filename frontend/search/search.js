import { FACETS, filter, facetCounts, encodeState, decodeState, pageHref, sourceHref, DEFAULT_SOURCE_BASE, kindOptions } from './search-core.js';
import { rankExport } from './full-search.js';

// ?index=<json url>   index file (default search-index.json next to this page)
// ?app=<url>          optional running rwiki app; default links open source pages
// ?src=<url prefix>   source browser prefix for the raw page (default GitHub jjd-wiki main)
const params = new URLSearchParams(location.search);
const INDEX_URL = params.get('index') || 'search-index.json';
const FULL_INDEX_URL = params.get('fullindex') || 'full-search-index.json';
const APP_BASE = params.get('app') || '';
const SRC_BASE = params.get('src') || DEFAULT_SOURCE_BASE;
const KIND_LABEL = { recipe: '配方', template: '模板', method: '方法', item: 'L0 条目', scenario: '场景', source: '来源', interface: '接口', 'chart-type': '图型', project: '课题', layout: '图样' };
const PACKAGE_LIMIT = 40;
const RESULT_LIMIT = 200;

const $ = (sel) => document.querySelector(sel);
const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v; else if (k === 'text') node.textContent = v; else node.setAttribute(k, v);
  }
  for (const kid of kids) if (kid != null) node.append(kid);
  return node;
};

const readState = () => {
  const extra = new URLSearchParams(location.hash.replace(/^#/, ''));
  return {...decodeState(location.hash), mode: extra.get('mode') || 'facets', scope: extra.get('scope') || 'knowledge', runnable: extra.get('runnable') === 'true'};
};
let index, fullIndex, fullError = '', fullLoading = false, state = readState(), labels = { domains: {}, charts: {} };

function setState(next) {
  state = { ...state, ...next };
  const encoded = new URLSearchParams(encodeState(state));
  if (state.mode === 'full') encoded.set('mode', 'full');
  if (state.scope === 'source') encoded.set('scope', 'source');
  if (state.runnable) encoded.set('runnable', 'true');
  const hash = encoded.toString();
  history.replaceState(null, '', hash ? `#${hash}` : location.pathname + location.search);
  render();
}

function label(facet, value) {
  const l = labels[facet] && labels[facet][value];
  return l && l !== value ? `${l}` : value;
}

function renderFacet(facet) {
  const section = document.querySelector(`[data-facet="${facet}"]`);
  const box = section.querySelector('.chips');
  const counts = facetCounts(index.entries, state, facet);
  const selected = new Set(state[facet]);
  let values = index.facets[facet].map((f) => f.value);
  if (facet === 'packages') {
    const needle = section.querySelector('.facet-filter').value.trim().toLowerCase();
    if (needle) values = values.filter((v) => v.toLowerCase().includes(needle));
  }
  // Selected first, then by live count, then by global order.
  values.sort((a, b) => (selected.has(b) - selected.has(a)) || ((counts.get(b) || 0) - (counts.get(a) || 0)));
  const total = values.length;
  if (facet === 'packages') values = values.slice(0, PACKAGE_LIMIT);
  box.replaceChildren(...values.map((v) => {
    const n = counts.get(v) || 0;
    const chip = el('button', { class: 'chip', type: 'button', 'aria-pressed': String(selected.has(v)), title: v },
      label(facet, v), el('span', { class: 'n', text: String(n) }));
    if (!n && !selected.has(v)) chip.setAttribute('disabled', '');
    chip.onclick = () => {
      const next = selected.has(v) ? state[facet].filter((x) => x !== v) : [...state[facet], v];
      setState({ [facet]: next });
    };
    return chip;
  }));
  if (total > values.length) box.append(el('span', { class: 'more', text: `另有 ${total - values.length} 个，输入包名筛选` }));
}

function renderResults() {
  if (state.mode === 'full') { renderFullResults(); return; }
  const hits = filter(index.entries, state);
  $('#count').textContent = `${hits.length} / ${index.entries.length} 条` + (hits.length > RESULT_LIMIT ? `（显示前 ${RESULT_LIMIT}）` : '');
  $('#results').replaceChildren(...hits.slice(0, RESULT_LIMIT).map((e) => {
    const source = sourceHref(SRC_BASE, e.page);
    const href = pageHref(APP_BASE, e.page) || source;
    const badges = el('div', { class: 'badges' },
      el('span', { class: 'badge', text: [KIND_LABEL[e.kind] || e.kind, e.level, e.status, e.run && `run:${e.run}`].filter(Boolean).join(' · ') }),
      ...e.charts.map((c) => el('span', { class: 'badge chart', text: `图型 ${label('charts', c)}` })),
      ...e.domains.map((d) => el('span', { class: 'badge domain', text: label('domains', d) })),
      ...e.unknown_tags.map((t) => el('span', { class: 'badge warn', title: '不在受控词表', text: `未入词表 ${t}` })),
      ...e.packages.map((p) => el('span', { class: 'badge pkg', text: p })));
    return el('li', {},
      el('div', {},
        href ? el('a', { class: 'title', href, text: e.title }) : el('span', { class: 'title', text: e.title }),
        el('span', { class: 'id', text: e.id }),
        source ? el('a', { class: 'src', href: source, target: '_blank', rel: 'noopener', text: '源文件' }) : null),
      e.summary ? el('p', { class: 'summary', text: e.summary }) : null,
      badges);
  }));
}

function renderFullResults() {
  const status = $('#full-status');
  if (!fullIndex) {
    $('#results').replaceChildren(); $('#count').textContent = '';
    status.textContent = fullError || '正在加载全文索引…';
    if (!fullError && !fullLoading) {
      fullLoading = true;
      fetch(FULL_INDEX_URL).then(response => {if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json();})
        .then(value => {fullIndex = value; render();})
        .catch(error => {fullError = `全文索引加载失败：${error.message}。运行 export_full_index.py 生成索引后刷新。`; render();})
        .finally(() => {fullLoading = false;});
    }
    return;
  }
  const hits = rankExport(fullIndex, state.q, {scope: state.scope, kind: state.kind, runnable: state.runnable, limit: 100});
  const coverage = fullIndex.coverage || {};
  status.textContent = !state.q.trim() ? '输入方法名、课题问题或代码关键词开始搜索。'
    : !hits.length ? '没有匹配结果。尝试中英文方法名、缩短关键词或切换范围。' : '按命中章节的相关性排序。资料状态与运行证据分别显示。';
  if (state.scope === 'source' && fullIndex.coverage?.scope !== 'source') status.textContent += ' 本索引未包含来源全文。';
  if (coverage.evidence === 'export_snapshot') status.textContent += ` 证据状态为导出时快照（${coverage.exported_at || '日期未记录'}），使用前请在本地应用重新核对。`;
  $('#count').textContent = `${hits.length} 条结果（最多显示 100 条）`;
  status.title = `覆盖范围：${JSON.stringify(coverage)}`;
  const availability = {available: '资料已在本机', not_downloaded: '未下载', missing: '资料缺失'};
  $('#results').replaceChildren(...hits.map(hit => {
    const base = pageHref(APP_BASE, hit.page);
    const href = base ? base + (hit.match_section ? `?${new URLSearchParams({section: hit.match_section})}` : '') : sourceHref(SRC_BASE, hit.page);
    return el('li', {},
      el('div', {}, href ? el('a', {class: 'title', href, text: hit.title}) : el('span', {class: 'title', text: hit.title}), el('span', {class: 'id', text: hit.id})),
      el('p', {class: 'summary', text: `命中章节：${hit.match_section || '正文'}`}),
      el('p', {class: 'summary', text: hit.snippet || hit.summary || ''}),
      el('p', {class: 'id', text: hit.source_path || hit.file_path || hit.page || ''}),
      el('div', {class: 'badges'}, el('span', {class: 'badge', text: availability[hit.asset_availability] || '资料状态未知'}),
        el('span', {class: 'badge', text: `运行证据：${hit.evidence_state || hit.run || '未记录'}`})),
      hit.asset_availability === 'not_downloaded' ? el('p', {class: 'meta', text: '资料未下载；连接本地应用后可通过“下载资料”按钮获取。'}) : null);
  }));
}

function render() {
  $('#q').value !== state.q && ($('#q').value = state.q);
  $('#kind').replaceChildren(el('option', {value: '', text: '全部类型'}),
    ...kindOptions(index, fullIndex, state.mode).map(k => el('option', {value: k.value, text: `${KIND_LABEL[k.value] || k.value}（${k.count}）`})));
  $('#kind').value = state.kind;
  $('#mode').value = state.mode;
  $('#scope').value = state.scope;
  $('#runnable').checked = state.runnable;
  $('#scope-label').hidden = $('#runnable-label').hidden = $('#full-status').hidden = state.mode !== 'full';
  document.querySelectorAll('[data-facet]').forEach(section => {section.hidden = state.mode === 'full';});
  FACETS.forEach(renderFacet);
  renderResults();
}

async function main() {
  try {
    const response = await fetch(INDEX_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    index = await response.json();
  } catch (error) {
    $('#meta').textContent = `索引加载失败（${INDEX_URL}：${error.message}）。先运行 build_index.py 生成 search-index.json。`;
    return;
  }
  for (const d of index.vocabulary.domains) labels.domains[d.value] = d.label || d.value;
  for (const c of index.vocabulary.charts) labels.charts[c.value] = c.label || c.value;
  const src = index.source || {};
  $('#meta').textContent = `${index.stats.entries} 条 · catalog sha256 ${String(src.catalog_sha256 || '').slice(0, 12)}`
    + (src.rev ? ` · rev ${src.rev}` : '') + ` · 生成于 ${index.generated_at}`;
  for (const k of index.facets.kinds) $('#kind').append(el('option', { value: k.value, text: `${KIND_LABEL[k.value] || k.value}（${k.count}）` }));
  $('#q').addEventListener('input', (ev) => setState({ q: ev.target.value }));
  $('#kind').addEventListener('change', (ev) => setState({ kind: ev.target.value }));
  document.querySelector('[data-facet="packages"] .facet-filter').addEventListener('input', () => renderFacet('packages'));
  $('#mode').onchange = event => setState({mode: event.target.value});
  $('#scope').onchange = event => setState({scope: event.target.value});
  $('#runnable').onchange = event => setState({runnable: event.target.checked});
  $('#reset').onclick = () => setState({ q: '', kind: '', charts: [], domains: [], packages: [], runnable: false, scope: 'knowledge' });
  addEventListener('hashchange', () => { state = readState(); render(); });
  render();
}

main();
