const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const root = __dirname;
const port = Number(process.env.PORT || 4173);
const types = { '.html':'text/html; charset=utf-8', '.css':'text/css; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.json':'application/json; charset=utf-8', '.svg':'image/svg+xml', '.md':'text/plain; charset=utf-8' };
http.createServer((request, response) => {
  let pathname;
  try { pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname); }
  catch { response.writeHead(400).end('Bad request'); return; }
  const target = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
  const relative = path.relative(root, target);
  if (relative.startsWith('..') || path.isAbsolute(relative) || relative.split(path.sep).some(s => s.startsWith('.'))) {
    response.writeHead(403).end('Forbidden'); return;
  }
  fs.readFile(target, (error, bytes) => {
    if (error) { response.writeHead(404).end('Not found'); return; }
    response.writeHead(200, { 'Content-Type': types[path.extname(target)] || 'application/octet-stream', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
    response.end(bytes);
  });
}).listen(port, '127.0.0.1', () => console.log(`Shift Lab ready at http://127.0.0.1:${port}`));
