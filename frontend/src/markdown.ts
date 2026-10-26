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
export function renderBody(body: string, env: RenderEnv, {
  dropUser = false,
  dropFacts = false,
  foldMethodDetails = false,
  dropSections = [] as string[],
} = {}): string {
  let src = body.replace(/^# .*\r?\n/, '');
  if (dropUser) src = src.replace(USER_BLOCK, '');
  const facts = src.match(/<!-- facts:start -->([\s\S]*?)<!-- facts:end -->\r?\n?/);
  if (dropFacts) src = src.replace(/<!-- facts:start -->[\s\S]*?<!-- facts:end -->\r?\n?/, '');
  src = src.replace(MARKERS, '');
  const dropped = new Set(dropSections);
  if (!foldMethodDetails && dropped.size === 0) return md.render(src, env);

  // Markdown token boundaries distinguish actual sections from headings inside fenced code.
  // Every canonical section survives unless explicitly dropped; presentation never changes source Markdown.
  const lines = src.split('\n');
  const headings = md.parse(src, env).flatMap((token, index, tokens) => token.type === 'heading_open' && token.tag === 'h2' && token.level === 0 && token.map
    ? [{ line: token.map[0], end: token.map[1], title: tokens[index + 1].content }]
    : []);
  let html = md.render(lines.slice(0, headings[0]?.line ?? lines.length).join('\n'), env);
  for (let i = 0; i < headings.length; i++) {
    const section = headings[i];
    if (dropped.has(section.title)) continue;
    const end = headings[i + 1]?.line ?? lines.length;
    const sectionBody = lines.slice(section.end, end).join('\n');
    if (foldMethodDetails && /^(参数|代码|源码|源代码|实现细节|来源|引用|许可证|历史|使用记录|知识关联)/.test(section.title)) {
      html += `<details class="method-details"><summary>${md.utils.escapeHtml(section.title)}</summary>${md.render(sectionBody, env)}</details>`;
    } else html += md.render(lines.slice(section.line, end).join('\n'), env);
  }
  if (dropFacts && facts?.[1].trim()) html += `<details class="method-details"><summary>来源元数据与派生记录</summary>${md.render(facts[1].replace(MARKERS, ''), env)}</details>`;
  return html;
}

export function renderMarkdown(src: string, env: RenderEnv): string {
  return md.render(src, env);
}

function methodSectionText(body: string, title: string): string {
  const userAt = body.indexOf('<!-- user:start -->');
  const agent = userAt >= 0 ? body.slice(0, userAt) : body;
  const start = new RegExp(`^## ${title}[ \\t]*\\r?\\n`, 'm').exec(agent);
  if (!start) return '';
  const rest = agent.slice(start.index + start[0].length);
  return rest.split(/\r?\n## /)[0].trim();
}

export function methodSection(body: string, title: string): string {
  return methodSectionText(body, title);
}

export function methodPurpose(body: string): string {
  return methodSectionText(body, '用途').split(/\r?\n\s*\r?\n/)[0];
}
