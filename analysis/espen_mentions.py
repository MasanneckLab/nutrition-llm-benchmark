#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Where the responses name ESPEN: in their own prose, and in their reference entries.

Produces for the manuscript (Results 3.5):
  ESPEN named in the body text of 142 of 180 responses (Open Evidence 49 of 60), in 58
  of them without an exact guideline reference; Open Evidence cited no ESPEN guideline,
  and three of its reference entries were other ESPEN publications.

Definitions
  body text        the response text without its source apparatus and without its
                   citations: the appended 'Sources:' block of Sonar Reasoning Pro and
                   the numbered reference list of Open Evidence are cut off, and every
                   bracketed bibliographic citation in the running text is removed (the
                   same rule as in extract_citations.py: a year and at least two commas).
                   What remains is what the system writes in its own words.
  ESPEN named      'ESPEN' or 'European Society for Clinical Nutrition', case-insensitive.
  reference entry  any extracted citation of the response (citations_long_v3.csv),
                   searched in raw text, title and journal.
  exact reference  consensus_guideline_reference = 'Yes' (ratings_raters.csv).

Two steps. With the raw rating workbooks available (NUTRITION_RAW), the script reads
the response texts and writes one flag per response to ../data/espen_mentions.csv.
Without them it counts from that deposited file, so the reported figures reproduce
from data/ alone. The file holds only the flags, no response text.

Note on an earlier count: a search computed alongside the first citation extraction
(1,387 citations, see archive/) gave 117 and 42, with a different separation of body
text, reference list and citations. The 49 for Open Evidence reproduces unchanged under
the rule used here.

Input
  $NUTRITION_RAW/Final_Konsens_Nutrition_master_rating_Konsensabgleich.xlsx  (optional)
  ../data/ratings_raters.csv
  ../data/citations_long_v3.csv
Output
  ../data/espen_mentions.csv   (written only when the raw data are available)

Requires openpyxl only for the first step.
"""
import csv, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
RAW = os.environ.get('NUTRITION_RAW')
CONSENSUS = 'Final_Konsens_Nutrition_master_rating_Konsensabgleich.xlsx'
OUT = os.path.join(DATA, 'espen_mentions.csv')

ORDER = ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']
ESPEN = re.compile(r'ESPEN|European Society for Clinical Nutrition', re.I)
BRACKET = re.compile(r'\[[^\[\]]{20,400}\]')


def is_citation(s):
    return bool(re.search(r'\b(19|20)\d{2}\b', s)) and s.count(',') >= 2


def body_text(model, t):
    """Response text without source apparatus and without bracketed citations."""
    if model == 'Sonar Reasoning Pro':
        i = t.find('Sources:')
        t = t[:i] if i >= 0 else t
    if model == 'Open Evidence':
        # the reference list starts with a line '1.' followed by a line '2.'
        lines = t.split('\n')
        for i, z in enumerate(lines):
            if z.strip() == '1.' and any(w.strip() == '2.' for w in lines[i + 1:i + 15]):
                t = '\n'.join(lines[:i])
                break
    return BRACKET.sub(lambda m: ' ' if is_citation(m.group(0)) else m.group(0), t)


def write_flags(ratings, citations):
    import openpyxl
    ws = openpyxl.load_workbook(os.path.join(RAW, CONSENSUS), data_only=True, read_only=True)['Rating']
    rows = list(ws.iter_rows(values_only=True))
    h = rows[0]
    text = {}
    for r in rows[1:]:
        d = dict(zip(h, r))
        if d.get('Rating ID'):
            text[d['Rating ID']] = d['Model answer'] or ''
    out = []
    for rid, r in sorted(ratings.items()):
        in_body = bool(ESPEN.search(body_text(r['model'], text[rid])))
        in_ref = any(ESPEN.search(' '.join((c['citation_raw_text'] or '', c['title'] or '', c['journal'] or '')))
                     for c in citations[rid])
        out.append(dict(rating_id=rid, model=r['model'],
                        espen_in_body_text=int(in_body), espen_in_reference_entry=int(in_ref)))
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    print('written: %s (%d rows)\n' % (OUT, len(out)))


def main():
    ratings = {r['rating_id']: r for r in csv.DictReader(open(os.path.join(DATA, 'ratings_raters.csv'), encoding='utf-8'))}
    citations = collections.defaultdict(list)
    for c in csv.DictReader(open(os.path.join(DATA, 'citations_long_v3.csv'), encoding='utf-8')):
        citations[c['rating_id']].append(c)

    if RAW:
        write_flags(ratings, citations)
    flags = list(csv.DictReader(open(OUT, encoding='utf-8')))

    body = [f for f in flags if f['espen_in_body_text'] == '1']
    not_exact = [f for f in body if ratings[f['rating_id']]['consensus_guideline_reference'] != 'Yes']
    by = lambda rs: '  '.join('%s %d' % (m.split()[0], sum(1 for r in rs if r['model'] == m)) for m in ORDER)
    print('ESPEN named in the body text          %3d of 180    %s' % (len(body), by(body)))
    print('  of these, no exact guideline reference %3d        %s' % (len(not_exact), by(not_exact)))

    oe_ref = sorted(f['rating_id'] for f in flags
                    if f['model'] == 'Open Evidence' and f['espen_in_reference_entry'] == '1')
    print('\nOpen Evidence, responses with ESPEN in a reference entry: %d' % len(oe_ref))
    for rid in oe_ref:
        for c in citations[rid]:
            s = ' '.join((c['citation_raw_text'] or '', c['title'] or '', c['journal'] or ''))
            if ESPEN.search(s):
                print('   %-15s category %-2s  %s' % (rid, c['category_code'], (c['title'] or c['citation_raw_text'])[:90]))
    print('   none of these entries is an ESPEN guideline; Open Evidence cited no ESPEN guideline.')
    print(REFERENCE)


REFERENCE = """
Reference values - a run must reproduce these:
  ESPEN named in the body text         142 of 180   Open Evidence 49   GPT-5.5 55   Sonar 38
    of these, no exact guideline ref.   58          Open Evidence 28   GPT-5.5 18   Sonar 12
  Open Evidence, ESPEN in a reference entry: 3 responses (NUTR-D2-4A-01, NUTR-D2-8A-04,
  NUTR-D3-2A-03): a symposium report and two expert group recommendations, no guideline.
"""

if __name__ == '__main__':
    main()
