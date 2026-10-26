/** Read-only boundary. Folder membership, explicit wikilinks and raw frontmatter only. */
export const CATEGORIES = [
  {id: 'layouts', title: '图样', en: 'Layouts', angle: 180, icon: 'works', color: '#c3bcf2'},
  {id: 'templates', title: '模板', en: 'Templates', angle: -125, icon: 'concept', color: '#e2e5e8'},
  {id: 'methods', title: '方法', en: 'Methods', angle: 0, icon: 'note', color: '#ace0cf'},
  {id: 'interfaces', title: '接口', en: 'Interfaces', angle: -40, icon: 'link', color: '#ecc98f'},
  {id: 'projects', title: '课题', en: 'Projects', angle: 40, icon: 'draft', color: '#acd6e8'}
];
const categorySet = new Set(CATEGORIES.map(c => c.id));
const administrative = /^(?:agents|index|readme|log|logs|changelog|_index|日志|索引)(?:[._ -]|$)/i;
export function categoryOf(path) {
  const parts = String(path).replace(/\\/g, '/').split('/');
  // Formal wiki entries live directly in these directories; nested files are evidence/assets.
  if (parts.length !== 2 || !categorySet.has(parts[0]) || !/\.md$/i.test(parts[1])) return null;
  if (administrative.test(parts[1])) return null;
  return parts[0];
}
export function parseWikiLinks(body) {
  // Obsidian's metadata cache is authoritative in production. Fallback for previews/cache startup.
  const text = body.replace(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/, '')
    .replace(/```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]*`|<!--[\s\S]*?-->/g, '');
  return [...text.matchAll(/(!?)\[\[([^\]\n]+)\]\]/g)].map(m => ({link: m[2].split('|')[0].trim(), displayText: m[2].split('|').slice(1).join('|').trim(), embed: !!m[1]}));
}
export function linkPath(link) {
  let target = String(link).split('|')[0].split('#')[0].trim().replace(/\\/g, '/');
  try { target = decodeURIComponent(target); } catch {}
  return target;
}
export function fallbackResolve(link, sourcePath, files) {
  const target = linkPath(link);
  if (!target) return files.find(f => f.path === sourcePath) || null;
  if (/^(?:[a-z]+:|\/\/)/i.test(target)) return null;
  const normalize = p => {
    const stack = [];
    for (const part of p.split('/')) {
      if (part === '..') { if (!stack.length) return null; stack.pop(); }
      else if (part && part !== '.') stack.push(part);
    }
    return stack.join('/');
  };
  const ext = /\.[a-z0-9]+$/i.test(target) ? '' : '.md';
  const normalized = normalize(target.replace(/^\//, '') + ext);
  const relative = normalize(sourcePath.slice(0, sourcePath.lastIndexOf('/') + 1) + target + ext);
  for (const candidate of target.startsWith('.') ? [relative] : [normalized, relative]) {
    const found = files.find(f => f.path === candidate);
    if (found) return found;
  }
  if (target.includes('/')) return null; // Never resolve a qualified link to an unrelated basename.
  const matches = files.filter(f => f.path.split('/').at(-1) === target + ext);
  return matches.length === 1 ? matches[0] : null;
}
export async function readGraph(vault, metadataCache) {
  const allFiles = vault.getMarkdownFiles();
  const files = allFiles.filter(f => categoryOf(f.path));
  const nodes = await Promise.all(files.map(async file => {
    const body = await vault.cachedRead(file);
    const cache = metadataCache.getFileCache(file);
    const fm = cache?.frontmatter || {};
    const title = typeof fm.title === 'string' && fm.title.trim() ? fm.title : file.basename || file.path.split('/').at(-1).replace(/\.md$/, '');
    const rawLinks = cache ? [...(cache.links || []), ...(cache.embeds || [])].map(l => ({...l, embed: (cache.embeds || []).includes(l)})) : parseWikiLinks(body);
    const kind = categoryOf(file.path);
    return {id: file.path, path: file.path, title, short: title, kind, body, rawStatus: fm.status, rawLinks, references: [], thumbnail: null, out: 0, in: 0, mutual: 0, deg: 0};
  }));
  nodes.sort((a, b) => a.path.localeCompare(b.path, 'zh-CN'));
  const index = new Map(nodes.map(n => [n.id, n]));
  const directed = new Set();
  let unresolved = 0;
  for (const node of nodes) {
    for (const raw of node.rawLinks) {
      const target = linkPath(raw.link);
      const destination = metadataCache.getFirstLinkpathDest(target, node.path);
      const label = raw.displayText || raw.link;
      // Only render existing local resources; no http/file/external resource loading.
      const isImage = /\.(?:png|jpe?g|gif|webp|svg|avif)$/i.test(destination?.path || '');
      if (raw.embed && isImage && !node.thumbnail) node.thumbnail = vault.adapter.getResourcePath(destination.path);
      if (raw.embed && isImage) continue;
      const resolvedNode = destination && index.get(destination.path);
      const resolved = !!resolvedNode;
      const excluded = !!destination && !resolved;
      node.references.push({link: raw.link, label, path: resolved ? destination.path : null, resolved, excluded});
      if (resolved && destination.path !== node.path) directed.add(JSON.stringify([node.path, destination.path]));
      else if (!destination) unresolved++;
    }
    if (!node.thumbnail) {
      const path = node.path.replace(/\.md$/i, '/thumb.png');
      if (vault.getAbstractFileByPath(path)) node.thumbnail = vault.adapter.getResourcePath(path);
    }
    delete node.rawLinks;
  }
  const links = [];
  for (const key of directed) {
    const [a, b] = JSON.parse(key), both = directed.has(JSON.stringify([b, a]));
    index.get(a).out++; index.get(b).in++;
    if (both) index.get(a).mutual++;
    if (!both || a < b) links.push({a, b, s: a, both, kind: 'wiki', w: both ? 2 : 1});
  }
  for (const n of nodes) n.deg = n.in + n.out;
  return {nodes, links, index, unresolved};
}
export function layoutGraph(graph) {
  const positions = {};
  for (const c of CATEGORIES) {
    const nodes = graph.nodes.filter(n => n.kind === c.id);
    const a = c.angle * Math.PI / 180;
    nodes.forEach((n, i) => {
      const r = 145 + Math.sqrt(i) * 34, spread = (i * 2.399963) % (Math.PI * .8) - Math.PI * .4;
      positions[n.id] = [Math.cos(a + spread) * r, Math.sin(a + spread) * r];
    });
  }
  return positions;
}
