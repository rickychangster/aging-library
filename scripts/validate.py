#!/usr/bin/env python3
"""
Validation tests for the Longevity & Wellness lecture library.

Usage:
  python3 scripts/validate.py

Checks three things:
  1. TAGS       — every tag string is in the taxonomy, counts are within schema
                  limits, related links resolve, ids match filenames.
  2. CORRECTNESS — schema completeness, valid dates, no duplicate ids, the
                  processed HTML file actually exists for every lecture.
  3. BIOMARKERS — the locked Option-B registry: typed edges (primary/driver/
                  predicts) resolve to real lectures, no edge overlap, valid
                  types, and the `primary` lecture really discusses the marker.

Exits non-zero if any check fails. Run before build.py / before committing.
See CLAUDE.md "Biomarkers — LOCKED DECISION" for the design contract.
"""

import json
import os
import re
import sys
from datetime import datetime

ROOT         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, 'catalog.json')
LECTURES_DIR = os.path.join(ROOT, 'lectures')

# Per-lecture tag-count limits (from CLAUDE.md catalog.json schema).
TAG_LIMITS = {
    'mechanism':    (1, 2),
    'system':       (1, 3),
    'theme':        (1, 2),
    'intervention': (0, 3),
}
MAX_DESC_WORDS   = 30
RELATED_RANGE    = (3, 4)

# At least one of these (case-insensitive substring) must appear in a
# biomarker's `primary` lecture HTML — guards against a mis-assigned primary.
BIOMARKER_KEYWORDS = {
    'vo2_max':              ['vo2', 'vo₂', 'cardiorespiratory'],
    'grip_strength':        ['grip strength', 'handgrip', 'sarcopenia'],
    'hrv':                  ['heart rate variability', 'hrv'],
    'gait_balance':         ['gait', 'balance', 'postural', 'sway'],
    'hearing_threshold':    ['hearing', 'audiogram', 'audiometry', 'decibel'],
    'hba1c_glucose':        ['hba1c', 'glucose', 'insulin', 'diabet'],
    'inflammatory_markers': ['crp', 'c-reactive', 'il-6', 'interleukin', 'inflamm'],
    'cortisol':             ['cortisol', 'hpa'],
    'testosterone':         ['testosterone', 'shbg', 'androgen'],
    'nad':                  ['nad', 'sirtuin'],
    'blood_pressure':       ['blood pressure', 'arterial', 'stiffness', 'crosslink'],
    'epigenetic_age':       ['methylation', 'epigenetic age', 'epigenetic clock'],
    'telomere_length':      ['telomere'],
    'multiomic_age':        ['multi-omic', 'multiomic', 'biological age', 'omic'],
    'microbiome_diversity': ['microbiome', 'gut microbi', 'diversity'],
    'sleep_architecture':   ['sleep architecture', 'rem', 'slow-wave', 'deep sleep'],
}


# ── PII guard ─────────────────────────────────────────────────────────────────
# Lecture SOURCES (Google Drive) are intentionally personal; build.py scrubs them
# on publish. These checks are the safety net: they fail if any personal value or
# age framing survives into the published files.
#
# The specific personal values are NOT hard-coded here (that would re-leak them):
# they are loaded from scripts/pii_rules.local.json (gitignored). This file keeps
# only generic, non-identifying patterns. If the local file is absent, the generic
# checks below still run.
PII_RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pii_rules.local.json')

# Secret-ish identifiers that must not appear in ANY tracked file (code or content).
PII_FORBIDDEN_GENERIC = [
    (r'changricky@gmail\.com',       'personal Google account email'),
    (r'Rickys?-MacBook',             'personal device hostname'),
]
# Checks that apply only to published *content* (not to code/docs that legitimately
# describe the rules, e.g. the literal phrase "your fifties" in build.py/CLAUDE.md).
PII_CONTENT_ONLY = [
    (r'\byour fifties\b',            'age framing (fifties)'),
]
# Heuristic: any second-person biomarker *reading* (a "your <marker> … <number>")
# is almost certainly personal data. The [^.<] stops before generic ranges like
# "(<1.0 mg/L)" so scrubbed text passes.
PII_HEURISTIC = re.compile(
    r'\byour\s+(hs-?crp|apob|ldl|hdl|tsh|insulin|homa-?ir|hba1c|glucose|'
    r'vitamin d|vo2|vo₂|telomere|cortisol|testosterone|lp\(a\))\b[^.<\n]{0,20}\d',
    re.I,
)


def load_pii_forbidden():
    """Generic patterns + per-value patterns from the local-only rules file."""
    patterns = [(p, label) for p, label in PII_FORBIDDEN_GENERIC]
    if os.path.exists(PII_RULES_PATH):
        with open(PII_RULES_PATH, encoding='utf-8') as f:
            spec = json.load(f)
        patterns += [(r['pattern'], r.get('label', 'personal value')) for r in spec.get('rules', [])]
    return patterns


class Validator:
    def __init__(self):
        self.errors = []
        self.checks = 0

    def check(self, condition, message):
        self.checks += 1
        if not condition:
            self.errors.append(message)
        return condition

    # ── load ────────────────────────────────────────────────────────────────
    def load(self):
        with open(CATALOG_PATH, encoding='utf-8') as f:
            self.catalog = json.load(f)
        self.taxonomy   = self.catalog.get('taxonomy', {})
        self.lectures   = self.catalog.get('lectures', [])
        self.biomarkers = self.catalog.get('biomarkers', {})
        self.ids        = {l.get('id') for l in self.lectures}

    # ── 1 + 2: tags & correctness ─────────────────────────────────────────────
    def validate_lectures(self):
        seen = set()
        for lec in self.lectures:
            lid = lec.get('id', '<missing id>')

            # schema completeness
            for key in ('id', 'title', 'description', 'filename', 'added', 'tags', 'related'):
                self.check(key in lec, f'[{lid}] missing required key "{key}"')

            # unique ids
            self.check(lid not in seen, f'[{lid}] duplicate id')
            seen.add(lid)

            # id <-> filename consistency
            self.check(
                lec.get('filename') == f'lectures/{lid}.html',
                f'[{lid}] filename should be "lectures/{lid}.html", got "{lec.get("filename")}"',
            )

            # processed HTML exists
            html_path = os.path.join(ROOT, lec.get('filename', ''))
            self.check(
                os.path.isfile(html_path),
                f'[{lid}] processed file not found: {lec.get("filename")} (run build.py)',
            )

            # added date format
            try:
                datetime.strptime(lec.get('added', ''), '%Y-%m-%d')
            except ValueError:
                self.errors.append(f'[{lid}] invalid "added" date: {lec.get("added")!r}')
            self.checks += 1

            # description length
            words = len(lec.get('description', '').split())
            self.check(
                0 < words <= MAX_DESC_WORDS,
                f'[{lid}] description is {words} words (max {MAX_DESC_WORDS})',
            )

            # tags: valid strings + counts
            tags = lec.get('tags', {})
            for facet, (lo, hi) in TAG_LIMITS.items():
                values = tags.get(facet, [])
                self.check(
                    lo <= len(values) <= hi,
                    f'[{lid}] {facet} has {len(values)} tags (allowed {lo}-{hi})',
                )
                self.check(
                    len(values) == len(set(values)),
                    f'[{lid}] {facet} has duplicate tags',
                )
                allowed = set(self.taxonomy.get(facet, []))
                for v in values:
                    self.check(v in allowed, f'[{lid}] {facet} tag not in taxonomy: {v!r}')

            # related links
            related = lec.get('related', [])
            lo, hi = RELATED_RANGE
            self.check(lo <= len(related) <= hi,
                       f'[{lid}] has {len(related)} related links (allowed {lo}-{hi})')
            self.check(len(related) == len(set(related)),
                       f'[{lid}] has duplicate related links')
            for rid in related:
                self.check(rid != lid, f'[{lid}] lists itself as related')
                self.check(rid in self.ids, f'[{lid}] related id does not exist: {rid}')

    # ── 3: biomarker registry ─────────────────────────────────────────────────
    def validate_biomarkers(self):
        valid_types = set(self.taxonomy.get('biomarker_type', []))
        self.check(bool(valid_types), 'taxonomy.biomarker_type is missing or empty')
        self.check(bool(self.biomarkers), 'no biomarkers defined in registry')

        for key, bm in self.biomarkers.items():
            # stable slug
            self.check(re.fullmatch(r'[a-z0-9_]+', key) is not None,
                       f'[biomarker:{key}] key must be snake_case [a-z0-9_]')

            # schema completeness
            for field in ('label', 'type', 'primary', 'driver', 'predicts'):
                self.check(field in bm, f'[biomarker:{key}] missing field "{field}"')

            # type in taxonomy
            self.check(bm.get('type') in valid_types,
                       f'[biomarker:{key}] type {bm.get("type")!r} not in biomarker_type taxonomy')

            # primary: exactly one real lecture
            primary = bm.get('primary')
            self.check(isinstance(primary, str) and primary in self.ids,
                       f'[biomarker:{key}] primary is not a valid lecture id: {primary!r}')

            # driver / predicts: lists of real, unique ids
            driver   = bm.get('driver', [])
            predicts = bm.get('predicts', [])
            for edge_name, edge in (('driver', driver), ('predicts', predicts)):
                self.check(isinstance(edge, list),
                           f'[biomarker:{key}] {edge_name} must be a list')
                if isinstance(edge, list):
                    self.check(len(edge) == len(set(edge)),
                               f'[biomarker:{key}] {edge_name} has duplicate ids')
                    for rid in edge:
                        self.check(rid in self.ids,
                                   f'[biomarker:{key}] {edge_name} id does not exist: {rid}')

            # no overlap across the three edges
            edge_ids = [primary] + list(driver) + list(predicts)
            self.check(len(edge_ids) == len(set(edge_ids)),
                       f'[biomarker:{key}] a lecture appears in more than one edge')

            # coverage/correctness: primary lecture actually discusses the marker
            keywords = BIOMARKER_KEYWORDS.get(key)
            self.check(keywords is not None,
                       f'[biomarker:{key}] no content keywords defined in validate.py')
            if keywords and isinstance(primary, str):
                html_path = os.path.join(ROOT, 'lectures', f'{primary}.html')
                if os.path.isfile(html_path):
                    with open(html_path, encoding='utf-8') as f:
                        text = f.read().lower()
                    self.check(
                        any(kw.lower() in text for kw in keywords),
                        f'[biomarker:{key}] primary lecture {primary} does not mention any of {keywords}',
                    )

    # ── PII: no personal data may reach published files ───────────────────────
    def validate_no_pii(self):
        # Applied to every tracked file: secret identifiers + the per-value rules.
        everywhere = [(re.compile(p, re.I), label) for p, label in load_pii_forbidden()]
        # Applied only to published content (not code/docs describing the rules).
        content_only = [(re.compile(p, re.I), label) for p, label in PII_CONTENT_ONLY]

        # (scripts/validate.py and pii_rules.local.json are excluded: the former
        # holds only generic patterns, the latter is the gitignored secret source.)
        content_files = sorted(
            [os.path.join(LECTURES_DIR, f) for f in os.listdir(LECTURES_DIR) if f.endswith('.html')]
            + [os.path.join(ROOT, 'index.html'), CATALOG_PATH, os.path.join(ROOT, 'privacy.html')]
        )
        code_files = [os.path.join(ROOT, 'CLAUDE.md'), os.path.join(ROOT, 'scripts', 'build.py')]

        for path in content_files + code_files:
            if not os.path.isfile(path):
                continue
            with open(path, encoding='utf-8') as f:
                text = f.read()
            name = os.path.relpath(path, ROOT)
            is_content = path in content_files
            for rx, label in everywhere:
                self.check(rx.search(text) is None,
                           f'[PII] {name}: {label} present (fix scrub rule / do not commit values)')
            if is_content:
                for rx, label in content_only:
                    self.check(rx.search(text) is None, f'[PII] {name}: {label} present')
                m = PII_HEURISTIC.search(text)
                self.check(m is None,
                           f'[PII] {name}: personalized biomarker reading {m.group(0)!r}' if m
                           else f'[PII] {name}: ok')

    # ── run ───────────────────────────────────────────────────────────────────
    def run(self):
        self.load()
        self.validate_lectures()
        self.validate_biomarkers()
        self.validate_no_pii()

        print(f'Lectures: {len(self.lectures)}   Biomarkers: {len(self.biomarkers)}   '
              f'Assertions run: {self.checks}')
        if self.errors:
            print(f'\nFAILED — {len(self.errors)} error(s):\n')
            for e in self.errors:
                print(f'  ✗ {e}')
            return 1
        print('\nPASSED — all checks green.')
        return 0


if __name__ == '__main__':
    sys.exit(Validator().run())
