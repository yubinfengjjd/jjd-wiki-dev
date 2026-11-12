import { FACETS, filter, facetCounts, encodeState, decodeState, pageHref, sourceHref } from './search-core.js';

// ?index=<json url>   index file (default search-index.json next to this page)
// ?app=<url>          optional running rwiki app; default links open source pages
// ?src=<url prefix>   source browser prefix for the raw page (default GitHub jjd-wiki main)
const params = new URLSearchParams(location.search);
const INDEX_URL = params.get('index') || 'search-index.json';
const APP_BASE = params.get('app') || '';
const SRC_BASE = params.get('src') || 'https://github.com/yubinfengjjd/jjd-wiki/blob/main/知识库/';
const KIND_LABEL = { recipe: '配方', template: '模板', method: '方法', item: 'L0 条目', scenario: '场景' };
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

let index, state = decodeState(location.hash), labels = { domains: {}, charts: {} };

function setState(next) {
  state = { ...state, ...next };
  const hash = encodeState(state);
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

function render() {
  $('#q').value !== state.q && ($('#q').value = state.q);
  $('#kind').value = state.kind;
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
  $('#reset').onclick = () => setState({ q: '', kind: '', charts: [], domains: [], packages: [] });
  addEventListener('hashchange', () => { state = decodeState(location.hash); render(); });
  render();
}

main();
