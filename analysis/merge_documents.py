#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version 3: extended duplicate detection.

Version 2 merged only records with a matching identifier (9 cases via the PubMed
identifier). Not detected were duplicates where the same guideline document
appears once bibliographically and once as an espen.org link. Version 3 adds the
document identity from document_identity.py.

In addition, flag_outdated_guideline_edition is redetermined: no longer via the
publication year but via the cited edition against the current one.

Input:  ../data/intermediate/citations_long_v2.csv  (built by build_long_table.py)
Output: ../data/intermediate/citations_long_v3.csv

The deposited ../data/citations_long_v3.csv is the output of the original run. A
rerun of the chain reproduces it in every field except first_mention_in_answer
for three rows (see build_long_table.py), so the rerun is written to intermediate/
and does not overwrite the deposit.
"""
import csv, collections, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from document_identity import espen_document, same_document, is_superseded

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
OUT = os.path.join(DATA, 'intermediate')
rows = list(csv.DictReader(open(os.path.join(OUT, 'citations_long_v2.csv'), encoding='utf-8')))
by = collections.defaultdict(list)
for r in rows:
    by[r['rating_id']].append(r)

merged, dropped = 0, set()
for rid, rs in by.items():
    idents = {id(x): espen_document(x) for x in rs}
    urls = [x for x in rs if x['source_format'] == 'url_list' and idents[id(x)]]
    used = set()
    for xb in rs:
        if xb['source_format'] not in ('bracket', 'both'):
            continue
        ib = idents[id(xb)]
        if not ib:
            continue
        for xu in urls:
            if id(xu) in used or id(xu) in dropped:
                continue
            if same_document(ib, idents[id(xu)]):
                xb['source_format'] = 'both'
                xb['url_also'] = xu['url']
                dropped.add(id(xu)); used.add(id(xu)); merged += 1
                break

out = [r for r in rows if id(r) not in dropped]

# --- redetermine replaced edition ---
alt_alt, alt_neu = 0, 0
for r in out:
    alt = r['flag_outdated_guideline_edition'] == '1'
    ident = espen_document(r)
    neu = is_superseded(ident)
    if alt: alt_alt += 1
    if neu: alt_neu += 1
    r['flag_outdated_guideline_edition'] = 1 if neu else 0
    r['cited_guideline_family'] = ident[0] if ident else ''
    r['cited_guideline_edition'] = ident[2] if ident else ''

with open(os.path.join(OUT, 'citations_long_v3.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

M = ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']
print('merged via document identity: %d' % merged)
print('citations_long_v3.csv  %d rows (before %d)' % (len(out), len(rows)))
print()
print('%-22s %-10s %s' % ('System', 'version 2', 'version 3'))
c2 = collections.Counter(r['model'] for r in rows); c3 = collections.Counter(r['model'] for r in out)
for m in M:
    print('%-22s %-10d %d' % (m, c2[m], c3[m]))
print()
print('%-22s %s' % ('Categories, Sonar', '  '.join('%-12s' % x for x in ['A', 'A*', 'B', 'D', 'F', '?'])))
for lbl, src in [('version 2', rows), ('version 3', out)]:
    s = [r for r in src if r['model'] == 'Sonar Reasoning Pro']
    cc = collections.Counter(r['category_code'] for r in s); n = len(s)
    print('%-22s %s' % (lbl, '  '.join('%-12s' % ('%d (%.1f %%)' % (cc[k], 100*cc[k]/n)) for k in ['A', 'A*', 'B', 'D', 'F', '?'])))
print()
print('replaced guideline edition, citations: %d (year rule) -> %d (edition comparison)' % (alt_alt, alt_neu))
for m in M:
    s = [r for r in out if r['model'] == m]
    a = len({r['rating_id'] for r in s if r['flag_outdated_guideline_edition'] == 1})
    print('   %-22s %d of 60 responses' % (m, a))

print("""
Reference values - a run must reproduce these:
  merged via document identity 13; rows 1475 -> 1462
  Open Evidence 431 / GPT-5.5 168 / Sonar 863
  replaced edition, responses: Open Evidence 0, GPT-5.5 38, Sonar 8 of 60
""")
