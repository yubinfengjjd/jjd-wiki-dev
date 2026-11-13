import {existsSync} from 'node:fs';
import {resolve, dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';

/** Canonical directories win even while a legacy copy still exists. */
export function findEngineRoot(start) {
  if (start instanceof URL) start = fileURLToPath(start);
  const parents = [];
  for (let current = resolve(start); ; current = dirname(current)) {
    parents.push(current);
    if (dirname(current) === current) break;
  }
  for (const relative of ['skills/research-wiki', 'staged/research-wiki']) {
    for (const parent of parents) {
      const candidate = join(parent, relative);
      if (existsSync(join(candidate, 'rwiki'))) return candidate;
    }
  }
  throw new Error('Cannot locate the research-wiki engine from ' + start);
}
