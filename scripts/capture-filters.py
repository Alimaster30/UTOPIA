"""Preserve query-based filters and their pagination without a WordPress backend."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit, urljoin, parse_qsl, urlencode
from html.parser import HTMLParser
import json, hashlib, html, re
from mirror import get, discover, local_path, sanitize, ROOT, PUBLIC, ORIGIN, MANIFEST

def query_links(source, base):
    class Links(HTMLParser):
        def __init__(self): super().__init__(); self.links=set()
        def handle_starttag(self, tag, attrs):
            value = dict(attrs).get('href', '')
            if tag == 'a' and value:
                url = urljoin(base, html.unescape(value))
                parsed = urlsplit(url)
                if parsed.netloc == urlsplit(ORIGIN).netloc and parsed.query and not Path(parsed.path).suffix and 'term=' in parsed.query:
                    self.links.add(parsed._replace(fragment='').geturl())
    p=Links(); p.feed(source); return p.links

m=json.loads(MANIFEST.read_text())
entries={x['source']:x for x in m['assets'] if '$' not in x['source'] and '%244' not in x['source']}
pending=set()
for p in (ROOT/'reference/pages').rglob('index.html'):
    rel=p.parent.relative_to(ROOT/'reference/pages').as_posix()
    base=ORIGIN+'/' if rel=='homepage' else ORIGIN+'/'+rel+'/'
    pending.update(query_links(p.read_text(encoding='utf-8'),base))
seen=set(); routes={}; sources={}; assets=set()
while pending:
    batch=sorted(pending-seen); pending=set()
    if not batch: break
    seen.update(batch)
    with ThreadPoolExecutor(max_workers=5) as pool:
        jobs={pool.submit(get,url):url for url in batch}
        for job in as_completed(jobs):
            url=jobs[job]
            try:
                data,mime=job.result(); source=data.decode('utf-8')
                sources[url]=source; assets.update(discover(source,url)); pending.update(query_links(source,url)-seen)
                print('FILTER',url,flush=True)
            except Exception as e: print('FILTER ERROR',url,str(e),flush=True)
    if len(seen)>100: raise RuntimeError('Unexpected query scope')
def capture(url):
    dest=local_path(url)
    if url in entries and entries[url]['status']=='downloaded' and dest.exists():return entries[url]
    data,mime=get(url); dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    return {'source':url,'local':dest.relative_to(PUBLIC).as_posix(),'bytes':len(data),'contentType':mime,'sha256':hashlib.sha256(data).hexdigest(),'status':'downloaded'}
with ThreadPoolExecutor(max_workers=6) as pool:
    jobs={pool.submit(capture,url):url for url in assets}
    for job in as_completed(jobs):
        url=jobs[job]
        try: entries[url]=job.result()
        except Exception as e:entries[url]={'source':url,'status':'failed','error':str(e)}
replacements={url:'/'+e['local'] for url,e in entries.items() if e['status']=='downloaded'}
for url,source in sources.items():
    parsed=urlsplit(url)
    key=parsed.path+'?'+urlencode(sorted(parse_qsl(parsed.query)))
    ident=hashlib.sha256(key.encode()).hexdigest()[:16]
    raw=ROOT/'reference/filters'/ident/'index.html';raw.parent.mkdir(parents=True,exist_ok=True);raw.write_text(source,encoding='utf-8')
    text=sanitize(source)
    for remote,local in sorted(replacements.items(),key=lambda item:-len(item[0])):
        text=text.replace(remote,local).replace(remote.replace('/','\\/'),local.replace('/','\\/'))
    for origin in (ORIGIN,'http://viewbook.tiltonschool.org','//viewbook.tiltonschool.org'):
        text=text.replace(origin,'').replace(origin.replace('/','\\/'),'')
    text=text.replace('href=""','href="/"').replace('data-page=""','data-page="/"')
    dest=PUBLIC/'filters'/ident/'index.html';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text,encoding='utf-8')
    routes[key]=dest.relative_to(PUBLIC).as_posix()
m['queryRoutes']=routes;m['assets']=list(entries.values())
MANIFEST.write_text(json.dumps(m,indent=2),encoding='utf-8')
(PUBLIC/'query-routes.json').write_text(json.dumps(routes,indent=2),encoding='utf-8')
print('DONE',len(routes),'filter/pagination variants',flush=True)
