import { createRequire } from 'node:module';
import { mkdtemp, unlink, rmdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = resolve(fileURLToPath(new URL('..', import.meta.url)));
const require = createRequire(join(root, 'package.json'));
const { build } = require('esbuild');
const dir = await mkdtemp(join(tmpdir(), 'rwiki-methods-'));
const outfile = join(dir, 'test.cjs');
try {
  await build({ entryPoints: [join(root, 'tests/methods.test.tsx')], outfile, bundle: true,
    platform: 'node', format: 'cjs', jsx: 'automatic', target: 'node22', logLevel: 'silent' });
  const result = spawnSync(process.execPath, [outfile], { encoding: 'utf8' });
  process.stdout.write(result.stdout); process.stderr.write(result.stderr);
  if (result.status) process.exitCode = result.status;
} finally { await unlink(outfile).catch(() => {}); await rmdir(dir); }
