import http from 'node:http';
import { createReadStream } from 'node:fs';
import { stat, readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), 'public');
const port = Number(process.env.PORT || 3000);
const host = process.env.HOST || '127.0.0.1';
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json', '.svg': 'image/svg+xml', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif', '.ico': 'image/x-icon', '.woff': 'font/woff', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.otf': 'font/otf', '.eot': 'application/vnd.ms-fontobject', '.mp4': 'video/mp4', '.webm': 'video/webm', '.mp3': 'audio/mpeg', '.pdf': 'application/pdf' };

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host}`);
    let pathname;
    try { pathname = decodeURIComponent(url.pathname); } catch { res.writeHead(400).end(); return; }
    let target = path.resolve(root, '.' + pathname);
    if (target !== root && !target.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
    if (pathname === '/wp-admin/admin-ajax.php' && req.method === 'POST') {
      let body = '';
      for await (const chunk of req) { body += chunk; if (body.length > 65536) { res.writeHead(413).end(); return; } }
      const params = new URLSearchParams(body);
      const action = params.get('action');
      const key = action === 'chooseGuide' ? 'chooseGuide' : action === 'slideshow' && /^\d+$/.test(params.get('id') || '') ? `slideshow-${params.get('id')}` : null;
      if (!key) { res.writeHead(400).end('Unknown local presentation action.'); return; }
      const fragment = await readFile(path.join(root, 'fragments', key + '.html'));
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }).end(fragment); return;
    }
    if (/^\/wp-json\/contact-form-7\/v1\/contact-forms\/\d+\/feedback\/schema\/?$/.test(pathname)) {
      res.writeHead(200, { 'Content-Type': 'application/json' }).end('{"rules":[]}'); return;
    }
    if (/^\/wp-json\/contact-form-7\/v1\/contact-forms\/\d+\/refill\/?$/.test(pathname) && req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'application/json' }).end('{}'); return;
    }
    if (pathname.startsWith('/menu/')) target = path.join(root, 'external', 'static.addtoany.com', pathname);
    if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405).end('This local clone does not submit data.'); return; }
    let info;
    try {
      if (url.searchParams.has('term')) {
        const routes = JSON.parse(await readFile(path.join(root, 'query-routes.json'), 'utf8'));
        const key = pathname + '?' + new URLSearchParams([...url.searchParams.entries()].sort()).toString();
        if (routes[key]) target = path.join(root, routes[key]);
      }
      info = await stat(target);
      if (info.isDirectory()) { target = path.join(target, 'index.html'); info = await stat(target); }
    } catch {
      if (pathname === '/wp-json/contact-form-7/v1/contact-forms/528/feedback/schema') {
        res.writeHead(200, { 'Content-Type': 'application/json' }).end('{"rules":[]}'); return;
      }
      res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end('<!doctype html><title>Page unavailable</title><main style="font:20px Georgia;padding:8vw;background:#faf6ef;min-height:70vh"><h1>This page is unavailable.</h1><p>The source website did not provide this page during capture.</p><a href="/">Return to the viewbook</a></main>'); return;
    }
    const headers = { 'Content-Type': types[path.extname(target)] || 'application/octet-stream', 'Accept-Ranges': 'bytes', 'Cache-Control': path.extname(target) === '.html' ? 'no-cache' : 'public, max-age=3600' };
    if (req.headers.range) {
      const match = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range);
      if (!match) { res.writeHead(416, { 'Content-Range': `bytes */${info.size}` }).end(); return; }
      const start = match[1] ? Number(match[1]) : Math.max(0, info.size - Number(match[2]));
      const end = match[1] && match[2] ? Math.min(Number(match[2]), info.size - 1) : info.size - 1;
      if (start > end || start >= info.size) { res.writeHead(416, { 'Content-Range': `bytes */${info.size}` }).end(); return; }
      res.writeHead(206, { ...headers, 'Content-Range': `bytes ${start}-${end}/${info.size}`, 'Content-Length': end - start + 1 });
      if (req.method === 'HEAD') res.end(); else createReadStream(target, { start, end }).pipe(res);
    } else {
      res.writeHead(200, { ...headers, 'Content-Length': info.size });
      if (req.method === 'HEAD') res.end(); else createReadStream(target).pipe(res);
    }
  } catch (error) { console.error(error.message); if (!res.headersSent) res.writeHead(500); res.end(); }
});
server.listen(port, host, () => console.log(`Tilton viewbook clone: http://${host}:${port}`));
