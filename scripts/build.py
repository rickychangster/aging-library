#!/usr/bin/env python3
"""
Build script for the Longevity & Wellness lecture library.

Usage:
  python3 scripts/build.py

What it does:
  1. Reads catalog.json
  2. Copies each lecture HTML from the source directory to lectures/
  3. Injects OG meta tags + analytics snippet into each lecture <head>
  4. Injects the related-articles widget block before </body>
  5. Embeds the full catalog into index.html (between CATALOG markers)
  6. Generates sitemap.xml and robots.txt

Run this after adding new entries to catalog.json.
"""

import json
import os
import re
from datetime import date

ROOT         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, 'catalog.json')
INDEX_PATH   = os.path.join(ROOT, 'index.html')
LECTURES_DIR = os.path.join(ROOT, 'lectures')
SOURCE_DIR   = os.path.expanduser(
    '~/Library/CloudStorage/GoogleDrive-changricky@gmail.com/My Drive/DailyLearning'
)

# ── Set your live site URL here after deploying ──────────────────────────────
# e.g. "https://yourname.github.io/aging-library"
SITE_URL = 'https://YOUR_USERNAME.github.io/aging-library'

# ── Plausible domain — set after creating your Plausible account ─────────────
# e.g. "yourname.github.io"  (leave empty to omit the analytics tag)
PLAUSIBLE_DOMAIN = ''


def load_catalog():
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_og_block(lecture):
    """Return <meta> tags to inject into a lecture's <head>."""
    title = lecture['title'] + ' — Longevity & Wellness'
    desc  = lecture.get('description', '')
    url   = f'{SITE_URL}/lectures/{os.path.basename(lecture["filename"])}'
    lines = [
        f'<meta name="description" content="{desc}">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{desc}">',
        f'<meta property="og:type" content="article">',
        f'<meta property="og:url" content="{url}">',
        f'<meta name="twitter:card" content="summary">',
        f'<meta name="twitter:title" content="{title}">',
        f'<meta name="twitter:description" content="{desc}">',
        f'<link rel="icon" type="image/svg+xml" href="../favicon.svg">',
    ]
    if PLAUSIBLE_DOMAIN:
        lines.append(
            f'<script defer data-domain="{PLAUSIBLE_DOMAIN}" '
            f'src="https://plausible.io/js/script.js"></script>'
        )
    return '\n'.join(lines)


def build_related_block(lecture, catalog_lectures):
    """Build the <script id="related-data"> block for one lecture."""
    id_to_lec = {l['id']: l for l in catalog_lectures}
    related_entries = []
    for rel_id in lecture.get('related', []):
        rel = id_to_lec.get(rel_id)
        if not rel:
            continue
        filename = os.path.basename(rel['filename'])
        tags = []
        for group in ('mechanism', 'theme'):
            t = rel.get('tags', {}).get(group, [])
            if t:
                tags.append(t[0])
        related_entries.append({
            'id':       rel['id'],
            'title':    rel['title'],
            'filename': filename,
            'tags':     tags,
        })

    payload = {'id': lecture['id'], 'related': related_entries}
    return (
        '\n<script id="related-data" type="application/json">\n'
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + '\n</script>\n'
        '<script src="../related-widget.js"></script>\n'
    )


def process_lecture(lecture, catalog_lectures):
    filename  = os.path.basename(lecture['filename'])
    src_path  = os.path.join(SOURCE_DIR, filename)
    dest_path = os.path.join(LECTURES_DIR, filename)

    if not os.path.exists(src_path):
        print(f'  SKIP  {filename} — not found in source directory')
        return

    with open(src_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Remove existing injections (idempotent re-runs)
    html = re.sub(
        r'\n?<!-- LW:META:BEGIN -->.*?<!-- LW:META:END -->\n?',
        '', html, flags=re.DOTALL
    )
    html = re.sub(
        r'\n?<script id="related-data"[^>]*>.*?</script>\s*'
        r'<script src="../related-widget\.js"></script>\s*',
        '', html, flags=re.DOTALL
    )

    # Inject OG tags into <head>
    og_block = f'<!-- LW:META:BEGIN -->\n{build_og_block(lecture)}\n<!-- LW:META:END -->'
    html = html.replace('</head>', og_block + '\n</head>', 1)

    # Inject related widget before </body>
    html = html.replace('</body>', build_related_block(lecture, catalog_lectures) + '</body>', 1)

    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'  OK    {filename}')


def embed_catalog_in_index(catalog):
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        index = f.read()

    catalog_json = json.dumps(catalog, ensure_ascii=False, indent=2)
    pattern = r'(<!-- CATALOG:BEGIN -->.*?<script id="catalog-data"[^>]*>)(.*?)(</script>.*?<!-- CATALOG:END -->)'
    replacement = r'\g<1>\n' + catalog_json + r'\n\g<3>'
    new_index, n = re.subn(pattern, replacement, index, flags=re.DOTALL)

    if n == 0:
        print('  WARN  Could not find CATALOG markers in index.html')
        return

    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        f.write(new_index)
    print(f'  OK    index.html ({len(catalog["lectures"])} lectures embedded)')


def generate_sitemap(lectures):
    today = date.today().isoformat()
    urls  = [f'  <url><loc>{SITE_URL}/</loc><lastmod>{today}</lastmod></url>']
    for lec in lectures:
        fname = os.path.basename(lec['filename'])
        added = lec.get('added', today)
        urls.append(f'  <url><loc>{SITE_URL}/lectures/{fname}</loc><lastmod>{added}</lastmod></url>')

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + '\n'.join(urls)
        + '\n</urlset>\n'
    )
    path = os.path.join(ROOT, 'sitemap.xml')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(sitemap)
    print(f'  OK    sitemap.xml ({len(lectures) + 1} URLs)')


def generate_robots():
    content = f'User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n'
    path = os.path.join(ROOT, 'robots.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('  OK    robots.txt')


def main():
    catalog  = load_catalog()
    lectures = catalog['lectures']

    os.makedirs(LECTURES_DIR, exist_ok=True)

    print(f'\nSource:  {SOURCE_DIR}')
    print(f'Output:  {LECTURES_DIR}')
    print(f'Site:    {SITE_URL}')
    print(f'Lectures in catalog: {len(lectures)}\n')

    print('Processing lectures:')
    for lec in lectures:
        process_lecture(lec, lectures)

    print('\nEmbedding catalog in index.html:')
    embed_catalog_in_index(catalog)

    print('\nGenerating sitemap + robots:')
    generate_sitemap(lectures)
    generate_robots()

    print('\nDone.\n')
    print('Next steps:')
    print('  1. Set SITE_URL in scripts/build.py to your GitHub Pages URL')
    print('  2. Set PLAUSIBLE_DOMAIN if using Plausible Analytics')
    print('  3. Uncomment the Plausible <script> in index.html <head>')
    print('  4. git add -A && git commit -m "..." && git push\n')
    print('Local preview:')
    print(f'  cd {ROOT} && python3 -m http.server 8000')
    print('  open http://localhost:8000\n')


if __name__ == '__main__':
    main()
