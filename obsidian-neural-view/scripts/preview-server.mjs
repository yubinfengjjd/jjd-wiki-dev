import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const types = {'.html':'text/html; charset=utf-8', '.js':'application/javascript', '.css':'text/css', '.mp4':'video/mp4', '.jpg':'image/jpeg', '.json':'application/json; charset=utf-8'};
http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://127.0.0.1');
    const relative = url.pathname === '/' ? 'preview/index.html' : decodeURIComponent(url.pathname).slice(1);
    const filename = path.resolve(root, relative);
    if (!filename.startsWith(root + path.sep)) { res.writeHead(403); res.end(); return; }
    const data = await fs.readFile(filename);
    res.writeHead(200, {'Content-Type': types[path.extname(filename)] || 'application/octet-stream', 'Cache-Control':'no-store'}); res.end(data);
  } catch { res.writeHead(404); res.end('Not found'); }
}).listen(5178, '127.0.0.1', () => console.log('Shared-renderer preview: http://127.0.0.1:5178 (local fixture only; no vault exposed)'));
