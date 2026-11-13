import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, mkdirSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import * as paths from '../build-paths.mjs';

test('build locates canonical engine from both frontend layouts and falls back to legacy', () => {
  assert.equal(typeof paths.findEngineRoot, 'function');
  const root = mkdtempSync(join(tmpdir(), 'rwiki-paths-'));
  try {
    const legacy = join(root, 'staged', 'research-wiki');
    const canonical = join(root, 'skills', 'research-wiki');
    mkdirSync(join(legacy, 'rwiki'), {recursive: true});
    assert.equal(paths.findEngineRoot(join(root, 'frontend')), legacy);
    mkdirSync(join(canonical, 'rwiki'), {recursive: true});
    assert.equal(paths.findEngineRoot(join(root, 'frontend')), canonical);
    assert.equal(paths.findEngineRoot(join(root, 'apps', 'web')), canonical);
    assert.equal(paths.findEngineRoot(pathToFileURL(join(root, 'apps', 'web'))), canonical);
  } finally {rmSync(root, {recursive: true, force: true});}
});
