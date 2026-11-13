import {build} from 'esbuild';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import postcss from 'postcss';
import selectorParser from 'postcss-selector-parser';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
await fs.mkdir(path.join(root, 'dist'), {recursive: true});
await build({absWorkingDir: root, entryPoints: ['src/main.jsx'], outfile: 'dist/main.js', bundle: true, external: ['obsidian'], format: 'cjs', platform: 'browser', target: 'es2020', jsx: 'automatic', define: {'process.env.NODE_ENV': '"production"'}, legalComments: 'eof', minify: false});
const css = postcss.parse(await fs.readFile(path.join(root, 'src/vendor/neural.css'), 'utf8'));
const keyframes = new Map();
css.walkAtRules(rule => {
  if (rule.name === 'property') { rule.remove(); return; }
  if (rule.name.endsWith('keyframes')) { const name = rule.params; keyframes.set(name, `rnv-${name}`); rule.params = `rnv-${name}`; }
});
css.walkRules(rule => {
  if (rule.parent.type === 'atrule' && rule.parent.name.endsWith('keyframes')) return;
  if (rule.selector === 'html, body') { rule.remove(); return; }
  rule.selector = selectorParser(selectors => selectors.each(selector => {
    selector.prepend(selectorParser.combinator({value: ' '}));
    selector.prepend(selectorParser.className({value: 'research-neural-view'}));
  })).processSync(rule.selector);
});
css.walkDecls(decl => {
  if (decl.prop === 'animation' || decl.prop === 'animation-name') for (const [before, after] of keyframes) decl.value = decl.value.replace(new RegExp(`(?<![\\w-])${before}(?![\\w-])`, 'g'), after);
});
const scoped = css.toString().replace(/--orb-m0\b/g, '--rnv-orb-m0').replace(/--cx\b/g, '--rnv-cx');
await fs.writeFile(path.join(root, 'dist/styles.css'), scoped + '\n' + await fs.readFile(path.join(root, 'src/ui/overrides.css'), 'utf8'));
for (const name of ['manifest.json', 'LICENSE', 'NOTICE.md', 'PROVENANCE.md']) await fs.copyFile(path.join(root, name), path.join(root, 'dist', name));
await fs.cp(path.join(root, 'licenses'), path.join(root, 'dist/licenses'), {recursive: true});
await fs.cp(path.join(root, 'media'), path.join(root, 'dist/media'), {recursive: true});
await fs.mkdir(path.join(root, 'preview-dist'), {recursive: true});
await build({absWorkingDir: root, entryPoints: ['preview/main.jsx'], outfile: 'preview-dist/preview.js', bundle: true, format: 'esm', platform: 'browser', target: 'es2020', jsx: 'automatic', define: {'process.env.NODE_ENV': '"production"'}, legalComments: 'eof'});
console.log('Built native plugin in dist/ and shared-renderer browser harness in preview-dist/.');
