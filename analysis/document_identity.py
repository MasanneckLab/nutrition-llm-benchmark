#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document identity for guideline documents.

Purpose: detect duplicates where the same document appears once bibliographically
and once as an espen.org link without a shared PMID or DOI. Example: bracket
citation "Volkert, 2019, ESPEN guideline on clinical nutrition and hydration in
geriatrics" next to the espen.org URL of the same guideline.

The identity has three parts:
    family    geriatrics | dementia | polymorbid | other ESPEN guideline
    variant   full | practical
    edition   year, where determinable

Two records count as the same document if family and variant agree and the
edition is either equal or undetermined on one side. The espen.org file names
carry the edition only partly; where it is missing, family and variant decide.
This is deliberately generous, because espen.org keeps one file per guideline and
updates it.
"""
import re

FAMILY = [
    ('geriatrics', r'geriatric'),
    ('dementia',   r'dementia'),
    ('polymorbid', r'polymorbid'),
    ('hospital',   r'hospital nutrition|hospital_nutrition'),
    ('home_en',    r'home[_ -]enteral'),
    ('definitions', r'definitions and terminology|terminology of clinical nutrition'),
]
# editions recognisable in the espen.org file name
URL_EDITION = [
    (r'dementia-update-2024', ('dementia', 'full', '2024')),
    (r'Dementia_ClinNutr2015', ('dementia', 'full', '2015')),
    (r'0909/Geriatrics\.pdf',  ('geriatrics', 'full', '2009')),
]


def family_of(text):
    t = (text or '').lower()
    for name, pat in FAMILY:
        if re.search(pat, t):
            return name
    return ''


def variant_of(text):
    return 'practical' if re.search(r'practical', (text or ''), re.I) else 'full'


def espen_document(rec):
    """(family, variant, edition) for a record, or None if not an ESPEN document."""
    url = rec.get('url') or ''
    if 'espen.org' in url.lower():
        for pat, ident in URL_EDITION:
            if re.search(pat, url, re.I):
                return ident
        fam = family_of(url)
        return (fam, variant_of(url), '') if fam else None
    blob = ' '.join(str(rec.get(k) or '') for k in ('title', 'journal', 'author', 'citation_raw_text', 'raw'))
    if not re.search(r'espen', blob, re.I):
        return None
    fam = family_of(blob)
    if not fam:
        return None
    year = rec.get('publication_year') or rec.get('year') or ''
    return (fam, variant_of(blob), year)


def same_document(a, b):
    if a is None or b is None:
        return False
    if a[0] != b[0] or a[1] != b[1]:
        return False
    if a[2] and b[2] and a[2] != b[2]:
        return False
    return True


# Current edition per family. Basis for the question whether a cited edition has
# been replaced, independent of the publication year of any citation.
CURRENT_EDITION = {'geriatrics': '2019', 'dementia': '2024', 'polymorbid': '2023'}


def is_superseded(ident):
    """True if the cited edition has been replaced by a newer one."""
    if not ident:
        return False
    fam, _variant, year = ident
    cur = CURRENT_EDITION.get(fam)
    if not cur or not year or not year.isdigit():
        return False
    return int(year) < int(cur)
