// Throwaway QA driver: open a URL in headless Chrome, run steps, evaluate JS, take screenshots.
// usage: node cdp.mjs <url> <steps.json> <outDir>
// steps: [{ "wait": ms } | { "eval": "js" } | { "shot": "name.png" } | { "click": [x, y] } | { "move": [x, y] } | { "size": [w, h] }]
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [url, stepsFile, outDir] = process.argv.slice(2);
const steps = JSON.parse(readFileSync(stepsFile, 'utf8'));
const chrome = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const port = 9300 + Math.floor(Math.random() * 500);
const proc = spawn(chrome, [
  '--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--hide-scrollbars',
  `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'cdp-'))}`, '--window-size=1440,900', 'about:blank',
]);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target;
for (let i = 0; i < 50 && !target; i++) {
  await sleep(200);
  try {
    target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === 'page');
  } catch {}
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r));
let id = 0;
const pending = new Map();
const logs = [];
ws.addEventListener('message', (e) => {
  const msg = JSON.parse(e.data);
  if (msg.id && pending.has(msg.id)) pending.get(msg.id)(msg);
  if (msg.method === 'Runtime.consoleAPICalled') logs.push(`console.${msg.params.type}: ${msg.params.args.map((a) => a.value ?? a.description).join(' ')}`);
  if (msg.method === 'Runtime.exceptionThrown') logs.push(`exception: ${msg.params.exceptionDetails.exception?.description ?? msg.params.exceptionDetails.text}`);
});
const send = (method, params = {}) =>
  new Promise((resolve) => {
    const n = ++id;
    pending.set(n, resolve);
    ws.send(JSON.stringify({ id: n, method, params }));
  });

await send('Runtime.enable');
await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url });
await sleep(1500);

for (const step of steps) {
  if (step.wait) await sleep(step.wait);
  if (step.size) await send('Emulation.setDeviceMetricsOverride', { width: step.size[0], height: step.size[1], deviceScaleFactor: 1, mobile: step.size[0] < 600 });
  if (step.eval) {
    const r = await send('Runtime.evaluate', { expression: step.eval, returnByValue: true, awaitPromise: true });
    console.log(`eval> ${step.eval.slice(0, 80)}\n  = ${JSON.stringify(r.result.result?.value ?? r.result.exceptionDetails?.text)}`);
  }
  for (const [kind, key] of [['move', 'mouseMoved'], ['click', 'mousePressed']]) {
    if (!step[kind]) continue;
    const [x, y] = step[kind];
    await send('Input.dispatchMouseEvent', { type: key, x, y, button: kind === 'click' ? 'left' : 'none', clickCount: 1 });
    if (kind === 'click') await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
  }
  if (step.shot) {
    const r = await send('Page.captureScreenshot', { format: 'png' });
    writeFileSync(join(outDir, step.shot), Buffer.from(r.result.data, 'base64'));
    console.log(`shot> ${step.shot}`);
  }
}
console.log(logs.join('\n') || '(no console output)');
ws.close();
proc.kill();
process.exit(0);
