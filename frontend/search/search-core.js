// Pure filtering logic for the static search page. No DOM, no dependencies,
// so it runs unchanged in the browser (ES module) and in `node --test`.

export const FACETS = ['charts', 'domains', 'packages'];

export const DEFAULT_SOURCE_BASE = 'https://github.com/yubinfengjjd/jjd-wiki/blob/main/wiki/';

export function kindOptions(index, fullIndex, mode) {
  if (mode !== 'full' || !fullIndex) return index?.facets?.kinds ?? [];
  const counts = new Map();
  for (const document of fullIndex.documents ?? []) {
    const kind = document.record?.kind;
    if (kind) counts.set(kind, (counts.get(kind) ?? 0) + 1);
  }
  return [...counts].sort(([a], [b]) => a.localeCompare(b)).map(([value, count]) => ({value, count}));
}

/** Whitespace-separated terms; every term must appear in the entry text. */
export function terms(query) {
  return String(query || '').toLowerCase().split(/\s+/).filter(Boolean);
}

/** Within a facet values are OR-ed; across facets and with the query, AND-ed. */
export function matches(entry, state, skip) {
  const text = entry._text || '';
  for (const term of terms(state.q)) if (!text.includes(term)) return false;
  if (state.kind && entry.kind !== state.kind) return false;
  for (const facet of FACETS) {
    if (facet === skip) continue;
    const wanted = state[facet] || [];
    if (wanted.length && !wanted.some((v) => (entry[facet] || []).includes(v))) return false;
  }
  return true;
}

export function filter(entries, state) {
  return entries.filter((e) => matches(e, state));
}

/** Counts per facet value among entries matching every other constraint. */
export function facetCounts(entries, state, facet) {
  const counts = new Map();
  for (const e of entries) {
    if (!matches(e, state, facet)) continue;
    for (const v of e[facet] || []) counts.set(v, (counts.get(v) || 0) + 1);
  }
  return counts;
}

/** Shareable state in the hash: #q=..&charts=a,b&domains=..&packages=..&kind=.. */
export function encodeState(state) {
  const p = new URLSearchParams();
  if (state.q) p.set('q', state.q);
  if (state.kind) p.set('kind', state.kind);
  for (const f of FACETS) if ((state[f] || []).length) p.set(f, state[f].join(','));
  return p.toString();
}

export function decodeState(hash) {
  const p = new URLSearchParams(String(hash || '').replace(/^#/, ''));
  const state = { q: p.get('q') || '', kind: p.get('kind') || '' };
  for (const f of FACETS) state[f] = (p.get(f) || '').split(',').filter(Boolean);
  return state;
}

/** Link to the entry page in the rwiki app (`#/page/<path>`), per-segment encoded. */
export function pageHref(appBase, page) {
  const base = safeBase(appBase);
  if (!page || !base) return '';
  const path = page.split('/').map(encodeURIComponent).join('/');
  return `${base.split('#')[0]}#/page/${path}`;
}

/** Accept web or relative links, including URL-parser protocol normalization. */
export function safeBase(value) {
  if (typeof value !== 'string' || !value.trim()) return '';
  try {
    const base = value.trim();
    const url = new URL(base, 'https://rwiki.invalid/');
    return ['http:', 'https:'].includes(url.protocol) ? base : '';
  } catch { return ''; }
}

export function sourceHref(sourceBase, page) {
  const base = safeBase(sourceBase);
  return base && page ? base + page.split('/').map(encodeURIComponent).join('/') : '';
}
