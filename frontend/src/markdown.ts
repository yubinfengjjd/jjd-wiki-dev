import MarkdownIt from 'markdown-it';
import { pageHref, wikiFile } from './api';

export interface RenderEnv {
  titles: Map<string, string>;
  hiddenSources?: Set<string>;
}

const md = new MarkdownIt({ html: false, linkify: true });

const IMAGE = /\.(png|jpe?g|gif|svg|webp)$/i;

/** Wiki targets are root-relative; a target without an extension is a page. */
export function normalizeTarget(raw: string): string {
  const target = raw.split('#')[0].trim();
  const last = target.split('/').pop() ?? '';
  return last.includes('.') ? target : `${target}.md`;
}

md.inline.ruler.before('link', 'wikilink', (state, silent) => {
  const src = state.src;
  const embed = src.charCodeAt(state.pos) === 0x21;
  const open = embed ? state.pos + 1 : state.pos;
  if (!src.startsWith('[[', open)) return false;
  const close = src.indexOf(']]', open + 2);
  if (close < 0) return false;
  const inner = src.slice(open + 2, close);
  if (!inner || inner.includes('\n')) return false;
  if (!silent) {
    const [target, label] = inner.split('|');
    const token = state.push(embed ? 'wiki_embed' : 'wiki_link', '', 0);
    token.meta = { target: normalizeTarget(target), label: label?.trim() };
  }
  state.pos = close + 2;
  return true;
});

// Code, data and other assets linked from a page body are files, not pages: open the raw bytes.
const ASSET = /\.(py|r|sh|txt|csv|json|ya?ml)$/i;

md.renderer.rules.wiki_link = (tokens, idx, _opts, env: RenderEnv) => {
  const { target, label } = tokens[idx].meta;
  if (env.hiddenSources?.has(target)) return '<span class="muted">原始来源已归档（保留溯源记录）</span>';
  if (ASSET.test(target)) {
    return `<a class="wikilink file" href="${wikiFile(target)}" target="_blank" rel="noreferrer">${md.utils.escapeHtml(label ?? target.split('/').pop()!)}</a>`;
  }
  const title = env.titles.get(target);
  const text = label ?? title ?? target.replace(/\.md$/, '').split('/').pop();
  const cls = title === undefined ? 'wikilink broken' : 'wikilink';
  return `<a class="${cls}" href="${pageHref(target)}">${md.utils.escapeHtml(text)}</a>`;
};

md.renderer.rules.wiki_embed = (tokens, idx, _opts, env: RenderEnv) => {
  const { target } = tokens[idx].meta;
  if (IMAGE.test(target)) return `<img class="embed" src="${wikiFile(target)}" alt="" loading="lazy">`;
  return md.renderer.rules.wiki_link!(tokens, idx, _opts, env, md.renderer);
};

const USER_BLOCK = /<!-- user:start -->\n?([\s\S]*?)<!-- user:end -->\n?/;
const MARKERS = /<!-- (facts|user):(start|end) -->\n?/g;

export const userBlock = (body: string) => body.match(USER_BLOCK)?.[1].trim() ?? '';

// The viewer shows the figure, so the image embeds right under the title (kept for Obsidian) are
// dropped; images further down the body are content and stay.
const LEAD_EMBEDS = /^(# [^\n]*\r?\n)(?:\s*!\[\[[^\]\n]+\.png\]\][ \t]*\r?\n)+/;
export const withoutLeadEmbeds = (body: string) => body.replace(LEAD_EMBEDS, '$1');

/** Render a page body; the H1 is shown by the view, the user block by the note editor. */
export function renderBody(body: string, env: RenderEnv, { dropUser = false, dropFacts = false } = {}): string {
  let src = body.replace(/^# .*\n/, '');
  if (dropUser) src = src.replace(USER_BLOCK, '');
  if (dropFacts) src = src.replace(/<!-- facts:start -->[\s\S]*?<!-- facts:end -->\r?\n?/, '');
  return md.render(src.replace(MARKERS, ''), env);
}

export function methodPurpose(body: string): string {
  const agent = body.split('<!-- user:start -->')[0];
  const start = /^## 用途[ \t]*\r?\n/m.exec(agent);
  return start ? agent.slice(start.index + start[0].length).trim().split(/\r?\n## /)[0].split(/\r?\n\s*\r?\n/)[0] : '';
}
