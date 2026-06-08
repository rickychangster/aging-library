---
name: publish-lectures
description: Add new lecture HTML files to the Longevity & Wellness library — catalog them, scrub personal PII, validate, build, and push. Use whenever the user says to add/publish/review new lectures, "update the library/index", or names new lecture_*.html files. Triggers include "review new files in the library", "add lecture_X to the catalog", "publish the library".
---

# Publish new lectures to the Longevity & Wellness library

End-to-end workflow to take new lecture HTML into the published site safely.
Read `CLAUDE.md` first — it is the source of truth for taxonomy, schema, and the
two LOCKED decisions (biomarker registry, PII). This skill operationalizes it.

## 0. Find what's new
- `git status` + `ls lectures/` to find untracked/new `lecture_*.html`.
- The canonical sources live in Google Drive (`LECTURE_SOURCE_DIR`, see build.py).
  **The Drive folder is often NOT mounted on this machine.** If so, the new files
  sitting in `lectures/` are raw, unprocessed copies (no `LW:META:BEGIN` marker)
  and still contain the author's personal biomarker values.
- Check processing state: `grep -c 'LW:META:BEGIN' lectures/<file>.html` → `0` means raw.

## 1. Catalog each new lecture (CLAUDE.md schema)
For every new lecture, read its `<title>`/`<h1>` and append an entry to
`catalog.json` (in the `lectures` array):
- `id` = filename without `.html`; `filename` = `lectures/<id>.html`.
- `description` ≤ 30 words, for curious non-experts.
- Tags use ONLY the exact taxonomy strings (mechanism 1-2, system 1-3, theme 1-2,
  intervention 0-3).
- `related` = 3–4 intellectually-connected existing lecture ids.
- Do NOT touch the `biomarkers` registry as part of routine adds (it's a separate
  locked subsystem — only edit it when explicitly asked).

## 2. PII scrub — the critical step
`scripts/pii_rules.local.json` (gitignored) maps personal readings → generic
teaching ranges. **The historical rules only matched marker-adjacent forms
(`hs-CRP of 0.3`) and the heuristic only catches `your <marker> … number`.**
Real lectures phrase readings many other ways that slip through BOTH:
- possessive: `yours is 0.3`, `your 0.3`, `your current 0.3`, `yours are 3.0 / 0.6`
- paren / label: `hs-CRP (0.3`, `HOMA-IR (0.6`, `Insulin: 3.0`, `ApoB: 132` (SVG)
- bare: `TG/HDL 0.84`, `GGT 15`, `ALT 14`

Known personal values to date: hs-CRP 0.3, ApoB 132 (& 67→132), insulin 3.0,
HOMA-IR 0.6, TG/HDL 0.84, GGT 15, ALT 14, TSH 3.69, vitamin D 35. The author's
own values are these "good/optimal" numbers; generic *elevated* examples in the
same lecture (e.g. `insulin 12.0, HOMA-IR 3.0`) are NOT personal — leave them.

Process:
1. Inventory every personal reading in the new (and, if auditing, all) lectures:
   ```bash
   python3 - <<'PY'
   import re,glob
   markers=r'hs-?crp|apob|tg/hdl|ldl|hdl|tsh|insulin|homa-?ir|vitamin d|ggt|\balt\b|cortisol|testosterone'
   poss=re.compile(r'\byours?\b(?:\s+(?:is|are|current|existing))?\s*[:\-—(]?\s*(\d+(?:\.\d+)?)',re.I)
   mk=re.compile(r'('+markers+r')\s*[:(]?\s*\(?(\d+(?:\.\d+)?)\b',re.I)
   for fn in sorted(glob.glob('lectures/*.html')):
       t=open(fn,encoding='utf-8').read()
       for m in list(poss.finditer(t))+list(mk.finditer(t)):
           s=max(0,m.start()-40);print(fn,'|',re.sub(r'<[^>]+>','',re.sub(r'\s+',' ',t[s:m.end()+15])))
   PY
   ```
2. For each personal phrasing not yet covered, add a rule to
   `pii_rules.local.json` (NEVER to tracked code). Order rules specific→general.
   Replacements must read naturally in context and contain no value.
3. Apply the scrub. If Drive is mounted, run `build.py` (it scrubs from source).
   If Drive is NOT mounted (raw files already in `lectures/`), scrub in place:
   ```bash
   python3 - <<'PY'
   import json,re,glob,os
   spec=json.load(open('scripts/pii_rules.local.json',encoding='utf-8'))
   rules=[(re.compile(r['pattern'],re.I),r['repl']) for r in spec['rules']]
   rules+=[(re.compile(r'\bin your fifties\b',re.I),'in midlife'),(re.compile(r'\byour fifties\b',re.I),'midlife')]
   for p in sorted(glob.glob('lectures/*.html'))+['index.html','catalog.json','privacy.html']:
       if not os.path.isfile(p):continue
       t=open(p,encoding='utf-8').read();o=t
       for rx,rp in rules:t=rx.sub(rp,t)
       if t!=o:open(p,'w',encoding='utf-8').write(t);print('scrubbed',p)
   PY
   ```
   In-place scrub is consistent with what a Drive rebuild produces, as long as the
   rules are complete. Per CLAUDE.md, fix the rules — never hand-edit values.

## 3. Build
```bash
LECTURE_SOURCE_DIR=/tmp/lw_src python3 scripts/build.py   # if using a temp source dir of raw copies
# or plain `python3 scripts/build.py` if Drive is mounted
```
build.py re-embeds the catalog into `index.html` and regenerates sitemap/robots.
It SKIPs any lecture whose source isn't found (already-processed files are
preserved), so a partial source dir is fine.

## 4. Validate — must be green
```bash
python3 scripts/validate.py    # tags, schema, related links, biomarkers, PII
```
**Then run an INDEPENDENT value-anchored sweep** (validate only checks the exact
rule patterns; a never-seen phrasing can still leak). Re-run the inventory script
from step 2 over `lectures/*.html` and confirm zero personal readings remain
(ignore generic elevated examples and `15–30%`-style ranges). Iterate until clean.

## 5. Commit & push (only when asked)
```bash
git add -A   # pii_rules.local.json is gitignored — confirm with: git status --porcelain | grep -i pii  (should be empty)
git commit -m "Add lectures: <titles> (+ PII scrub)"
git push
```
GitHub Pages updates within ~60s. **Never commit `pii_rules.local.json` or any
personal value.** If validation fails, do not push.

## Notes
- The published repo's git *history* may still contain previously-leaked values;
  scrubbing the working tree does not purge history. Flag this to the user; a
  history rewrite + force-push is a separate, explicit decision.
