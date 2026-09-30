"""Generate a readable catalog and portable archive from verified captured assets."""
from pathlib import Path
import json,csv,collections,zipfile

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'asset-manifest.json').read_text())
assets=sorted((x for x in manifest['assets'] if x['status']=='downloaded'),key=lambda x:x['local'])
with (root/'assets.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['Source URL','Local path','Content type','Bundled bytes','Bundled SHA-256'])
    for a in assets:w.writerow([a['source'],'public/'+a['local'],a['contentType'],a['bundledBytes'],a['bundledSha256']])
types=collections.Counter(a['contentType'] for a in assets)
text='# Collected Tilton assets\n\n'
text+=f"Captured {len(assets)} assets, totaling {sum(a['bundledBytes'] for a in assets)/1024/1024:.1f} MiB. The manifest and CSV link each file to its source URL and include SHA-256 hashes of the local bundled files.\n\n"
text+='| Content type | Count |\n| --- | --- |\n'
text+=''.join(f'| {mime} | {count} |\n' for mime,count in sorted(types.items()))
text+='\nPhotos, SVGs, video and narration: `public/wp-content/uploads/`. Fonts and theme artwork: `public/wp-content/themes/tilton/assets/`. Styles and animation libraries: `public/wp-content/cache/autoptimize/`.\n\n'
text+='The zip contains only the manifest-listed files, preserving their folder structure, plus `asset-manifest.json` and `assets.csv`. Source pages and application code are kept in the project separately. YouTube/Vimeo streams remain external. Two decorative source files were unavailable and are listed in the manifest.\n'
(root/'ASSETS.md').write_text(text,encoding='utf-8')
with zipfile.ZipFile(root/'tilton-assets.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
    for a in assets:z.write(root/'public'/a['local'],a['local'])
    for name in ('asset-manifest.json','assets.csv','ASSETS.md'):z.write(root/name,name)
print(f'Packaged {len(assets)} assets; zip size {(root/"tilton-assets.zip").stat().st_size/1024/1024:.1f} MiB')
