import { readFile, readdir, stat, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const publicRoot = path.join(root, 'public');
const manifestPath = path.join(root, 'asset-manifest.json');
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
const missing = [];
const warnings = [];
const knownMissing = new Set(manifest.assets.filter(x => x.status === 'failed').map(x => new URL(x.source).pathname));
let pageCount = 0;
let referencedAssets = 0;
async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const target = path.join(dir, entry.name);
    if (entry.isDirectory()) files.push(...await walk(target)); else files.push(target);
  }
  return files;
}
function resolveReference(ref, file) {
  ref = ref.replace(/&amp;|&#038;/g, '&').trim();
  if (!ref || /^(data:|https?:|\/\/|#|javascript:|mailto:|tel:)/.test(ref)) return null;
  ref = ref.split(/[?#]/)[0];
  try { ref = decodeURIComponent(ref); } catch { return null; }
  if (!/\.(css|js|svg|png|jpe?g|webp|gif|ico|woff2?|ttf|eot|otf|mp4|webm|mp3|pdf)$/i.test(ref)) return null;
  return ref.startsWith('/') ? path.join(publicRoot, ref) : path.resolve(path.dirname(file), ref);
}
for (const file of await walk(publicRoot)) {
  const extension = path.extname(file);
  if (!['.html', '.css'].includes(extension)) continue;
  if (path.basename(file) === 'index.html' && !file.includes(`${path.sep}external${path.sep}`)) pageCount++;
  const text = await readFile(file, 'utf8');
  const refs = [...text.matchAll(/(?:src|data-src|poster|data-bg|href)\s*=\s*["']([^"']+)["']/g)].map(x => x[1]);
  refs.push(...[...text.matchAll(/url\(\s*["']?([^"')]+)["']?\s*\)/g)].map(x => x[1]));
  for (const ref of refs) {
    const target = resolveReference(ref, file);
    if (!target) continue;
    referencedAssets++;
    try { await stat(target); }
    catch {
      const item = { file: path.relative(publicRoot, file), reference: ref };
      const relative = '/' + path.relative(publicRoot, target).replaceAll(path.sep, '/');
      if (knownMissing.has(relative)) warnings.push(item); else missing.push(item);
    }
  }
}
const unavailablePages = [];
for (const source of manifest.pages) {
  const target = path.join(publicRoot, new URL(source).pathname, 'index.html');
  try { await stat(target); } catch { unavailablePages.push(source); }
}
manifest.unavailablePages = unavailablePages;
let assetBytes = 0;
for (const asset of manifest.assets.filter(x => x.status === 'downloaded')) {
  const target = path.join(publicRoot, asset.local);
  try {
    const bytes = await readFile(target);
    asset.bundledBytes = bytes.length;
    asset.bundledSha256 = createHash('sha256').update(bytes).digest('hex');
    assetBytes += bytes.length;
  } catch { missing.push({ file: 'asset-manifest.json', reference: asset.local }); }
}
await writeFile(manifestPath, JSON.stringify(manifest, null, 2));
const report = { pageCount, capturedAssets: manifest.assets.filter(x => x.status === 'downloaded').length, assetBytes, referencedAssets, missingLocalAssets: missing, unavailableSourceAssets: manifest.assets.filter(x => x.status === 'failed'), unavailablePages, knownSourceReferences: warnings };
await writeFile(path.join(root, 'verification-report.json'), JSON.stringify(report, null, 2));
console.log(`${pageCount} pages, ${report.capturedAssets} assets (${(assetBytes / 1024 / 1024).toFixed(1)} MiB). Checked ${referencedAssets} local resource references.`);
console.log(`${missing.length} unexpected missing resources; ${warnings.length} references to unavailable source assets; ${unavailablePages.length} unavailable source page.`);
if (missing.length) { console.error(JSON.stringify(missing.slice(0, 30), null, 2)); process.exitCode = 1; }
