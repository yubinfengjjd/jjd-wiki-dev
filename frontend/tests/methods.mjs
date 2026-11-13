import { createRequire } from 'node:module';
import { mkdtemp, unlink, rmdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = resolve(fileURLToPath(new URL('..', import.meta.url)));
const require = createRequire(join(root, 'package.json'));
const { build } = require('esbuild');
// Each suite runs in its own process: the API caches are module singletons.
const suites = ['methods.test.tsx', 'v2-pages.test.tsx', 'discovery-loading.test.tsx', 'global-search.test.tsx'];
const dir = await mkdtemp(join(tmpdir(), 'rwiki-methods-'));
try {
  for (const suite of suites) {
    const outfile = join(dir, suite.replace(/\.tsx$/, '.cjs'));
    try {
      await build({ entryPoints: [join(root, 'tests', suite)], outfile, bundle: true,
        platform: 'node', format: 'cjs', jsx: 'automatic', target: 'node22', logLevel: 'silent' });
      const result = spawnSync(process.execPath, [outfile], { encoding: 'utf8' });
      process.stdout.write(result.stdout); process.stderr.write(result.stderr);
      if (result.status) process.exitCode = result.status;
    } finally { await unlink(outfile).catch(() => {}); }
  }
} finally { await rmdir(dir); }
