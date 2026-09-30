"""Capture dependencies observed loading dynamically in the reference browser."""
import json, hashlib
from pathlib import Path
from mirror import get, local_path, MANIFEST, ORIGIN, PUBLIC

urls = [
 'https://cdnjs.cloudflare.com/ajax/libs/jquery-mousewheel/3.1.13/jquery.mousewheel.min.js',
 'https://static.addtoany.com/menu/modules/core.iho16r34.js',
 'https://static.addtoany.com/menu/sm.25.html',
 'https://static.addtoany.com/menu/svg/icons/facebook.js',
 'https://static.addtoany.com/menu/svg/icons/x.js',
 'https://static.addtoany.com/menu/svg/icons/link.js',
]
m = json.loads(MANIFEST.read_text())
for url in urls:
 data, mime = get(url)
 dest = local_path(url); dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)
 m['assets'] = [x for x in m['assets'] if x['source'] != url]
 m['assets'].append({'source':url, 'local':dest.relative_to(PUBLIC).as_posix(), 'bytes':len(data), 'contentType':mime, 'sha256':hashlib.sha256(data).hexdigest(), 'status':'downloaded'})
 print(url, len(data))
for p in PUBLIC.rglob('*.js'):
 if '/external/' in p.as_posix() and 'static.addtoany.com' not in p.as_posix(): continue
 text = p.read_text(encoding='utf-8', errors='replace')
 text = text.replace('https://cdnjs.cloudflare.com/ajax/libs/jquery-mousewheel/3.1.13/jquery.mousewheel.min.js', '/external/cdnjs.cloudflare.com/ajax/libs/jquery-mousewheel/3.1.13/jquery.mousewheel.min.js')
 # AddToAny uses its script URL to select its module base automatically.
 text = text.replace('https://static.addtoany.com/menu/', '/external/static.addtoany.com/menu/')
 text = text.replace('import(`/menu/svg/icons/', 'import(`/external/static.addtoany.com/menu/svg/icons/')
 p.write_text(text, encoding='utf-8')
MANIFEST.write_text(json.dumps(m, indent=2), encoding='utf-8')
