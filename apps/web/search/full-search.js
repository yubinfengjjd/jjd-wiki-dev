// Browser counterpart of rwiki.search.rank_export. The Python exporter owns the
// corpus, aliases and statistics; this module only ranks that immutable snapshot.
const normalize = value => String(value ?? '').toLowerCase();
const escapeRE = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
export function queryTokens(value, tokenizer = {}) {
  let text = normalize(value);
  for (const word of [...(tokenizer.stopwords ?? [])].sort((a, b) => b.length - a.length)) text = text.split(word).join('');
  const tokens = new Set(text.match(/[a-z0-9]+/g) ?? []);
  for (const part of text.match(/[\u3400-\u9fff]+/g) ?? []) {
    if (part.length === 1) tokens.add(part);
    else for (let i = 0; i < part.length - 1; i++) tokens.add(part.slice(i, i + 2));
  }
  (tokenizer.aliases ?? []).forEach((group, index) => {
    if (group.some(alias => {
      const word = normalize(alias);
      return /[\u3400-\u9fff]/.test(word) ? text.includes(word) : new RegExp(`(^|[^a-z0-9])${escapeRE(word)}($|[^a-z0-9])`).test(text);
    })) tokens.add(`@${index}`);
  });
  return tokens;
}

function snippet(text, tokens) {
  const clean = String(text ?? '').replace(/<!--[\s\S]*?-->/g, '').replace(/\s+/g, ' ').trim();
  const folded = normalize(clean);
  const positions = [...tokens].filter(token => !token.startsWith('@')).map(token => folded.indexOf(token)).filter(pos => pos >= 0);
  const start = Math.max(0, (positions.length ? Math.min(...positions) : 0) - 60);
  return (start ? '…' : '') + clean.slice(start, start + 220) + (start + 220 < clean.length ? '…' : '');
}


function normalizedPhrase(value, tokenizer = {}) {
  return String(value ?? '').replace(/<!--[\s\S]*?-->/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
}

export function queryPhrases(query, tokenizer = {}, ranking = {}) {
  const quoted = [...String(query).matchAll(/"([^"\n]+)"|“([^”\n]+)”/g)].map(m => m[1] || m[2]);
  const result = [];
  for (const value of quoted.length ? quoted : [query]) {
    let phrase = normalizedPhrase(value, tokenizer);
    if (!quoted.length) {
      const prefixes=[...(tokenizer.stopwords ?? [])].sort((a,b)=>b.length-a.length);
      while (phrase) {
        const prefix=prefixes.find(word=>word && phrase.startsWith(word));
        if (!prefix) break;
        phrase=phrase.slice(prefix.length).trimStart();
      }
    }
    if (phrase.length > (ranking.phrase_max_length ?? 120)) continue;
    if ((phrase.match(/[a-z0-9]+/g) ?? []).length < 2 && (phrase.match(/[\u3400-\u9fff]/g) ?? []).length < 4) continue;
    if (phrase && !result.includes(phrase)) result.push(phrase);
    if (result.length >= (ranking.phrase_limit ?? 4)) break;
  }
  return result;
}

function matchedPhrases(record, section, phrases, tokenizer) {
  const fields = [record.title ?? '', record.summary ?? '', section.title, section.text].map(x=>normalizedPhrase(x,tokenizer));
  return phrases.filter(phrase => {
    const pattern = (/^[a-z0-9]/.test(phrase) ? '(^|[^a-z0-9])' : '') + escapeRE(phrase) + (/[a-z0-9]$/.test(phrase) ? '(?![a-z0-9])' : '');
    return fields.some(field=>new RegExp(pattern).test(field));
  });
}

export function rankExport(index, query, options = {}) {
  if (!String(query ?? '').trim()) return [];
  const tokens = queryTokens(query, index.tokenizer);
  const {k1 = 1.2, b = .75} = index.ranking;
  const phrases = queryPhrases(query,index.tokenizer,index.ranking);
  const phraseWeight = Math.max(0,Math.min(.5,Number(index.ranking.phrase_weight ?? 0)));
  const {document_count: count, average_length: average, df} = index.statistics;
  const scope = options.scope ?? 'knowledge';
  if ((index.coverage?.scope ?? 'knowledge') !== scope) return [];
  const hits = [];
  for (const document of index.documents) {
    const record = document.record;
    if ((options.kind && record.kind !== options.kind)
      || (options.level && record.level !== options.level) || (options.runnable && !(record.usable || record.run === 'pass'))) continue;
    let best, bestScore = 0, bestPhrases = [];
    for (const section of document.sections) {
      let score = 0;
      for (const token of [...tokens].sort()) {
        const tf = section.tf[token] ?? 0;
        if (!tf) continue;
        const frequency = df[token] ?? 0;
        const idf = Math.log(1 + (count - frequency + .5) / (frequency + .5));
        score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * section.length / Math.max(1, average)));
      }
      const matched = phrases.length && phraseWeight ? matchedPhrases(record,section,phrases,index.tokenizer) : [];
      score *= 1 + phraseWeight * matched.length / Math.max(1,phrases.length);
      if (score > bestScore) { best = section; bestScore = score; bestPhrases = matched; }
    }
    if (best) hits.push({...record, score: Math.round(bestScore * 1e6) / 1e6,
      match_section: best.title, snippet: snippet(best.text, tokens), why: [`正文 BM25 · ${best.title}`, ...(bestPhrases.length ? [`精确短语 · ${bestPhrases.join('；')}`] : [])]});
  }
  hits.sort((a, b) => b.score - a.score || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  return hits.slice(0, Math.max(0, Math.min(options.limit ?? 10, 1000)));
}
