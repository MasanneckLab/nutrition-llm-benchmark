#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Applies the unchanged category rule of version 1 to the citations of version 2.
The rule itself was not touched; it is imported from archive/classify_citations_v1.py.

Input:  ../data/intermediate/citations_raw_v2.csv
Output: ../data/intermediate/classified_citations_v2.csv
"""
import csv, os, importlib.util, collections
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'data', 'intermediate')
spec = importlib.util.spec_from_file_location(
    'c1', os.path.join(HERE, '..', 'archive', 'classify_citations_v1.py'))
c1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(c1)

recs = list(csv.DictReader(open(os.path.join(OUT, 'citations_raw_v2.csv'), encoding='utf-8')))
for r in recs:
    cat, why, old = c1.classify(r)
    r['category'] = cat; r['reason'] = why; r['outdated_flag'] = 'yes' if old else ''
with open(os.path.join(OUT, 'classified_citations_v2.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(recs[0].keys())); w.writeheader(); w.writerows(recs)

print('%-22s %6s  %s' % ('System', 'n', '  '.join('%-13s' % x for x in
      ['A applicable', 'A* short', 'B other GL', 'C review', 'D independ.', 'F non-sci.', '? open'])))
for m in ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']:
    s = [r for r in recs if r['model'] == m]; c = collections.Counter(r['category'] for r in s); n = len(s)
    print('%-22s %6d  %s' % (m, n, '  '.join('%-13s' % ('%d (%.1f %%)' % (c[k], 100*c[k]/n))
          for k in ['A', 'A*', 'B', 'C', 'D', 'F', '?'])))

print("""
Reference values - a run must reproduce these (before category revision):
  Open Evidence   431   B 100  C 99  D 232
  GPT-5.5         168   A 53   A* 1  B 48   D 66
  Sonar           876   A 68   B 103  D 340  F 214  ? 151
""")
