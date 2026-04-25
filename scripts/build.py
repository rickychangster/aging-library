#!/usr/bin/env python3
"""
Build script for the Longevity & Wellness lecture library.

Usage:
  python3 scripts/build.py

What it does:
  1. Reads catalog.json
  2. Copies each lecture HTML from the source directory to lectures/
  3. Injects the related-articles widget block before </body>
  4. Embeds the full catalog into index.html (between CATALOG markers)

Run this after adding new entries to catalog.json.
"""

import json
import os
import shutil
import re

ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, 'catalog.json')
INDEX_PATH   = os.path.join(ROOT, 'index.html')
LECTURES_DIR = os.path.join(ROOT, 'lectures')
SOURCE_DIR   = os.path.expanduser(
    '~/Library/CloudStorage/GoogleDrive-changricky@gmail.com/My Drive/DailyLearning'
)

def load_catalog():
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_related_block(lecture, catalog_lectures):
    """Build the <script id="related-data"> block for one lecture."""
    id_to_lec = {l['id']: l for l in catalog_lectures}
    related_entries = []
    for rel_id in lecture.get('related', []):
        rel = id_to_lec.get(rel_id)
        if not rel:
            continue
        # filename is relative to the lectures/ directory (same folder)
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

    payload = {
        'id':      lecture['id'],
        'related': related_entries,
    }
    block = (
        '\n<script id="related-data" type="application/json">\n'
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + '\n</script>\n'
        '<script src="../related-widget.js"></script>\n'
    )
    return block

def process_lecture(lecture, catalog_lectures):
    filename   = os.path.basename(lecture['filename'])
    src_path   = os.path.join(SOURCE_DIR, filename)
    dest_path  = os.path.join(LECTURES_DIR, filename)

    if not os.path.exists(src_path):
        print(f'  SKIP  {filename} — not found in source directory')
        return

    with open(src_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Remove any existing widget injection (idempotent re-runs)
    html = re.sub(
        r'\n?<script id="related-data"[^>]*>.*?</script>\s*'
        r'<script src="../related-widget\.js"></script>\s*',
        '',
        html,
        flags=re.DOTALL
    )

    # Inject before </body>
    block = build_related_block(lecture, catalog_lectures)
    html  = html.replace('</body>', block + '</body>', 1)

    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'  OK    {filename}')

def embed_catalog_in_index(catalog):
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        index = f.read()

    catalog_json = json.dumps(catalog, ensure_ascii=False, indent=2)

    # Replace content between <!-- CATALOG:BEGIN --> and <!-- CATALOG:END -->
    pattern = r'(<!-- CATALOG:BEGIN -->.*?<script id="catalog-data"[^>]*>)(.*?)(</script>.*?<!-- CATALOG:END -->)'
    replacement = r'\g<1>\n' + catalog_json + r'\n\g<3>'
    new_index, n = re.subn(pattern, replacement, index, flags=re.DOTALL)

    if n == 0:
        print('  WARN  Could not find CATALOG markers in index.html')
        return

    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        f.write(new_index)
    print(f'  OK    index.html (catalog embedded, {len(catalog["lectures"])} lectures)')

def main():
    catalog = load_catalog()
    lectures = catalog['lectures']

    os.makedirs(LECTURES_DIR, exist_ok=True)

    print(f'\nSource: {SOURCE_DIR}')
    print(f'Output: {LECTURES_DIR}')
    print(f'Lectures in catalog: {len(lectures)}\n')

    print('Processing lectures:')
    for lec in lectures:
        process_lecture(lec, lectures)

    print('\nEmbedding catalog in index.html:')
    embed_catalog_in_index(catalog)

    print('\nDone.\n')
    print('To preview locally:')
    print('  cd ' + ROOT)
    print('  python3 -m http.server 8000')
    print('  open http://localhost:8000\n')

if __name__ == '__main__':
    main()
