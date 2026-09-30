"""Reproducible public-site capture. Only follows links on the supplied origin."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote, quote, urlencode
from urllib.request import Request, urlopen
import hashlib, html, json, re, time, posixpath, sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://viewbook.tiltonschool.org'
PUBLIC = ROOT / 'public'
REFERENCE = ROOT / 'reference'
MANIFEST = ROOT / 'asset-manifest.json'
EXTENSIONS = {'.css', '.js', '.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.otf', '.eot', '.mp4', '.webm', '.mp3', '.pdf', '.json'}
SKIP_HOSTS = ('googletagmanager.com', 'google-analytics.com', 'google.com', 'nr-data.net', 'newrelic.com')

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = set(); self.assets = set()
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for name, value in attrs.items():
            if not value: continue
            if tag == 'a' and name == 'href': self.links.add(value)
            if name in ('src', 'data-src', 'poster', 'data-poster', 'href'):
                if tag != 'a' or Path(urlsplit(value).path).suffix.lower() in EXTENSIONS:
                    self.assets.add(value)
            if name in ('srcset', 'data-srcset'):
                self.assets.update(x.strip().split(' ')[0] for x in value.split(','))

def get(url):
    parsed = urlsplit(url)
    if parsed.netloc == urlsplit(ORIGIN).netloc and not parsed.query and not Path(parsed.path).suffix:
        cached = REFERENCE / 'pages' / (parsed.path.strip('/') or 'homepage') / 'index.html'
        if cached.exists(): return cached.read_bytes(), 'text/html'
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0 (local reference capture)'}), timeout=90) as r:
                return r.read(), r.headers.get_content_type()
        except Exception:
            if attempt == 2: raise
            time.sleep(attempt + 1)

def clean_url(value, base):
    value = html.unescape(value).replace('\\/', '/').strip().strip('"\'')
    if not value or value.startswith(('data:', 'javascript:', 'mailto:', 'tel:', '#')): return None
    url = urljoin(base, value)
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https'): return None
    if any(parsed.hostname and parsed.hostname.endswith(h) for h in SKIP_HOSTS): return None
    # WP version query strings do not change these captured resources.
    normalized = posixpath.normpath(parsed.path or '/')
    if parsed.path.endswith('/') and not normalized.endswith('/'): normalized += '/'
    scheme = 'https' if parsed.netloc == urlsplit(ORIGIN).netloc else parsed.scheme
    return parsed._replace(scheme=scheme, path=quote(unquote(normalized), safe='/@:+'), fragment='', query='').geturl()

def local_path(url):
    p = urlsplit(url)
    path = unquote(p.path).lstrip('/')
    if '..' in Path(path).parts: raise ValueError('Unsafe source path')
    if p.netloc != urlsplit(ORIGIN).netloc:
        path = 'external/' + p.netloc + '/' + path
    return PUBLIC / path

def discover(text, base, css=False):
    found = set()
    if not css:
        parser = Parser(); parser.feed(text)
        found.update(parser.assets)
    found.update(re.findall(r'https?://[^\s<>"\'`\\)]+', text.replace('\\/', '/')))
    found.update(re.findall(r'url\(\s*["\']?([^\)"\']+)', text))
    if css:
        found.update(re.findall(r'@import\s+["\']([^"\']+)', text))
    result = set()
    for value in found:
        url = clean_url(value, base)
        if url and '$' not in unquote(url) and urlsplit(url).netloc in ('viewbook.tiltonschool.org', 'cdnjs.cloudflare.com', 'static.addtoany.com', 'fonts.gstatic.com', 'img.youtube.com') and Path(urlsplit(url).path).suffix.lower() in EXTENSIONS:
            result.add(url)
    return result

def sanitize(text):
    # Preserve the original design; remove production tracking/verification code.
    text = re.sub(r'<script\b[^>]*>.*?</script>', lambda m: '' if any(x in m[0] for x in ('NREUM', 'googletagmanager.com', 'gtag(', 'google-recaptcha-js', 'wpcf7-recaptcha-js')) else m[0], text, flags=re.S|re.I)
    text = re.sub(r'<noscript\b[^>]*>.*?</noscript>', '', text, flags=re.S|re.I)
    text = re.sub(r'<iframe\b[^>]*(?:googletagmanager|src="ns )[^>]*>.*?</iframe>', '', text, flags=re.S|re.I)
    text = re.sub(r'<link\b[^>]*(?:rel=["\'](?:canonical|alternate|EditURI|https://api.w.org/)|rel=["\']preconnect)[^>]*>', '', text, flags=re.I)
    text = text.replace('</body>', '<script src="/clone-local.js" defer></script></body>')
    return text

def main():
    PUBLIC.mkdir(exist_ok=True); (REFERENCE / 'pages').mkdir(exist_ok=True)
    pages, pending, assets, external_links = {}, {ORIGIN + '/'}, set(), set()
    while pending:
        batch = sorted(pending); pending = set()
        with ThreadPoolExecutor(max_workers=5) as pool:
            jobs = {pool.submit(get, url): url for url in batch}
            for job in as_completed(jobs):
                url = jobs[job]
                try:
                    data, mime = job.result()
                    if mime != 'text/html': continue
                    text = data.decode('utf-8')
                    pages[url] = text
                    p = Parser(); p.feed(text)
                    assets.update(discover(text, url))
                    for link in p.links:
                        target = clean_url(link, url)
                        if not target: continue
                        parsed = urlsplit(target)
                        if parsed.netloc != urlsplit(ORIGIN).netloc:
                            external_links.add(target); continue
                        if parsed.path.startswith(('/wp-', '/feed', '/tag/', '/author/', '/category/')): continue
                        if Path(parsed.path).suffix: continue
                        if target not in pages and target not in batch: pending.add(target)
                    print(f'PAGE {len(pages):3} {url}', flush=True)
                except Exception as e:
                    pages[url] = None; print(f'PAGE ERROR {url}: {e}', flush=True)
        if len(pages) > 160: raise RuntimeError('Unexpectedly large crawl; review scope')
    # These two public AJAX actions only return presentation markup. Capture them
    # so the original guide and slideshow controls work without WordPress.
    fragments = {}
    fragment_jobs = {'chooseGuide': {'action': 'chooseGuide'}}
    for url, source in pages.items():
        if not source: continue
        class Slides(HTMLParser):
            def handle_starttag(self, tag, attrs):
                d = dict(attrs)
                if 'slideshow-post' in d.get('class', '') and d.get('data-id'):
                    ident = d['data-id']
                    fragment_jobs['slideshow-' + ident] = {'action': 'slideshow', 'id': ident, 'page': d.get('data-page', url)}
        Slides().feed(source)
    for key, payload in fragment_jobs.items():
        try:
            req = Request(ORIGIN + '/wp-admin/admin-ajax.php', data=urlencode(payload).encode(), headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/x-www-form-urlencoded'})
            with urlopen(req, timeout=90) as response: fragment = response.read().decode('utf-8')
            fragments[key] = fragment
            assets.update(discover(fragment, ORIGIN + '/'))
            print('FRAGMENT ' + key, flush=True)
        except Exception as error: print(f'FRAGMENT ERROR {key}: {error}', flush=True)
    entries = {}
    if MANIFEST.exists():
        entries = {x['source']: x for x in json.loads(MANIFEST.read_text())['assets'] if x['status'] == 'downloaded' and urlsplit(x['source']).netloc in ('viewbook.tiltonschool.org', 'cdnjs.cloudflare.com', 'static.addtoany.com', 'fonts.gstatic.com', 'img.youtube.com')}
    seen = set()
    while assets:
        batch = sorted(assets - seen); assets = set()
        if not batch: break
        seen.update(batch)
        def download(url):
            dest = local_path(url)
            if dest.exists() and dest.stat().st_size and entries.get(url, {}).get('status') == 'downloaded':
                data = dest.read_bytes(); mime = entries[url]['contentType']
            else:
                data, mime = get(url); dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)
            entry = {'source': url, 'local': dest.relative_to(PUBLIC).as_posix(), 'bytes': len(data), 'contentType': mime, 'sha256': hashlib.sha256(data).hexdigest(), 'status': 'downloaded'}
            more = discover(data.decode('utf-8', errors='replace'), url, css=True) if dest.suffix in ('.css', '.js', '.svg') else set()
            return entry, more
        with ThreadPoolExecutor(max_workers=6) as pool:
            jobs = {pool.submit(download, url): url for url in batch}
            for job in as_completed(jobs):
                url = jobs[job]
                try:
                    entry, more = job.result(); entries[url] = entry; assets.update(more)
                    print(f'ASSET {len(entries):4} {entry["bytes"]:10} {url}', flush=True)
                except Exception as e:
                    entries[url] = {'source': url, 'status': 'failed', 'error': str(e)}
                    print(f'ASSET ERROR {url}: {e}', flush=True)
                MANIFEST.write_text(json.dumps({'origin': ORIGIN, 'capturedDate': '2026-09-30', 'pages': sorted(pages), 'externalLinks': sorted(external_links), 'assets': list(entries.values())}, indent=2), encoding='utf-8')
    replacements = {url: '/' + e['local'] for url, e in entries.items() if e['status'] == 'downloaded'}
    def rewrite(text):
        for source, local in sorted(replacements.items(), key=lambda x: -len(x[0])):
            text = text.replace(source, local).replace(source.replace('/', '\\/'), local.replace('/', '\\/'))
        for origin in (ORIGIN, 'http://viewbook.tiltonschool.org', '//viewbook.tiltonschool.org'):
            text = text.replace(origin, '').replace(origin.replace('/', '\\/'), '')
        text = text.replace('href=""', 'href="/"').replace('data-page=""', 'data-page="/"')
        return text
    for key, fragment in fragments.items():
        dest = PUBLIC / 'fragments' / (key + '.html')
        dest.parent.mkdir(parents=True, exist_ok=True); dest.write_text(rewrite(fragment), encoding='utf-8')
    for url, source in pages.items():
        if not source: continue
        slug = urlsplit(url).path.strip('/')
        raw = REFERENCE / 'pages' / (slug or 'homepage') / 'index.html'
        raw.parent.mkdir(parents=True, exist_ok=True); raw.write_text(source, encoding='utf-8')
        dest = PUBLIC / slug / 'index.html'
        dest.parent.mkdir(parents=True, exist_ok=True); dest.write_text(rewrite(sanitize(source)), encoding='utf-8')
    for url, entry in entries.items():
        if entry['status'] != 'downloaded': continue
        dest = PUBLIC / entry['local']
        if dest.suffix in ('.css', '.js', '.svg'):
            text = dest.read_text(encoding='utf-8', errors='replace')
            if dest.suffix == '.js':
                text = '\n'.join(line for line in text.split('\n') if not line.startswith('document.addEventListener("DOMContentLoaded",(e=>{var t;wpcf7_recaptcha='))
            dest.write_text(rewrite(text), encoding='utf-8')
    print(f'DONE: {len(pages)} pages, {len(entries)} assets', flush=True)

if __name__ == '__main__': main()
