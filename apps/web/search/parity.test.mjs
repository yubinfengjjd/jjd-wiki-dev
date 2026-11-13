import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve, dirname} from 'node:path';
import {rankExport} from './full-search.js';
import {findEngineRoot} from '../build-paths.mjs';

const directory = dirname(fileURLToPath(import.meta.url));
const fixturePath = resolve(findEngineRoot(directory), 'tests/fixtures/search-parity.json');
const fixture = JSON.parse(readFileSync(fixturePath, 'utf8'));
for (const [number, item] of fixture.cases.entries()) {
  test(`Python/JavaScript full result parity ${number + 1}: ${item.query || '(blank)'}`, () => {
    assert.deepEqual(rankExport(fixture.index, item.query, item.options), item.results);
  });
}
