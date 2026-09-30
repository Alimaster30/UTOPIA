# Tilton School Viewbook local clone

Source: https://viewbook.tiltonschool.org/

Captured: 30 September 2026

This project preserves the reference site's original HTML, CSS, typography, media, and JavaScript animations. It includes 50 ordinary pages, 13 category-filter/pagination variants, and the guide/slideshow AJAX fragments. The original Queens and Calibre fonts, icon font, campus map, photographs, MP3 narration, and three directly hosted MP4 videos are stored locally.

## Run

Node.js 20 or newer is sufficient. There are no npm dependencies to install.

```powershell
cd D:\Projects\UTOPIA
npm run dev
```

Open http://127.0.0.1:3000/. Set `PORT` if port 3000 is occupied. The server listens on loopback by default.

```powershell
npm run build
npm run smoke
```

`build` checks the captured files and their local references; this static capture does not need a bundling step. `smoke` checks the running local server. The Node server must be used to preserve query-based filters, AJAX overlays, and video byte-range playback. Opening the HTML directly from the filesystem will not provide those behaviors.

## Files

| Location | Contents |
| --- | --- |
| `public/index.html` | Original homepage, localized for the clone |
| `public/experience`, `public/get-inspired`, `public/student-tour`, `public/explore`, `public/visit` | Captured pages |
| `public/wp-content/uploads` | Photography, SVG artwork, video and audio |
| `public/wp-content/themes/tilton/assets` | Original fonts, icons, map artwork and theme resources |
| `public/wp-content/cache/autoptimize` | Original site styles and JavaScript bundles with local adaptations |
| `public/fragments` | Captured guide picker and slideshow responses |
| `public/filters`, `public/query-routes.json` | Query-based filter and pagination snapshots |
| `public/clone-local.js` | Local form submission guard |
| `server.mjs` | Local routes, presentation-only AJAX and media range serving |
| `asset-manifest.json`, `assets.csv`, `ASSETS.md` | Asset URLs, local paths, types, sizes and hashes |
| `tilton-assets.zip` | Generated locally with `python scripts/package-assets.py`; excluded from Git |
| `verification-report.json` | Resource validation results |
| `reference/pages`, `reference/filters` | Local capture output containing unmodified source HTML; excluded from Git |
| `reference/screenshots` | Browser verification screenshots |

## Preserved behavior and local adaptations

The original menu, scroll animation, guide carousel, student tour transitions, campus map, video lightbox, article overlays, galleries, filters and pagination use the original scripts. Two public WordPress presentation actions (`chooseGuide` and `slideshow`) are served from captured fragments. Query filters serve their captured response instead of requiring a WordPress installation.

Production analytics, New Relic and reCAPTCHA loading have been removed. The unused embedded contact form is guarded against submission, with a local-preview message. The original Request Info and Apply links still point to the school's external admissions services. YouTube/Vimeo videos and external admissions destinations require an internet connection; the three source-hosted MP4s and eleven MP3 files are local. No WordPress administration, live admissions backend or deployment is included.

One source page returned 404: `/how-tilton-can-help-you-excel-at-your-sport/`. Its article is available at `/experience/how-tilton-can-help-you-excel-at-your-sport/`, but the original broken link is preserved rather than silently changing the reference. Two decorative source files also returned 404: `assets/images/icons/calendar.svg` and `assets/images/marker-dec.svg`. These are recorded in the manifest and validation report.

This is a snapshot of the linked public viewbook as captured on the date above, not a live CMS. To refresh the capture:

```powershell
npm run capture
python scripts/package-assets.py
```

The Python capture scripts use the standard library. Browser verification was performed on desktop and at a 390-pixel mobile breakpoint. A few animation warnings from the original shared theme may appear on pages where its tour selectors do not exist.
