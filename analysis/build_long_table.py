#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builds the long citation table (version 2) from the classified citations.

This step assigns citation identifiers, topic numbers, the first-mention flag and
the grey-source flags, and reduces the classification output to the columns kept
in the deposited table. It sits between classify_citations.py and
merge_documents.py.

The script was reconstructed on 2 Sep 2026 from the deposited citations_long_v2.csv,
because the original build step had not been kept as a file. Checked field by field
against that table it agrees in every column except first_mention_in_answer, where
the original set 0 for three Sonar Reasoning Pro URL citations (CIT2-0484, -0574,
-0886) that have no earlier record with the same document key in the same response.
The original rule for those three cannot be recovered; the flag enters no reported
figure. The rules encoded here are:

  citation_id                 CIT2-0001 ... in file order
  question_id                 '<domain>|<question id>'
  topic_id                    1-30 across domains: (domain number - 1) * 10 + question number
  first_mention_in_answer     1 for the first record of a document within a
                              response, 0 for repeated mentions; document identity
                              as in extract_citations.doc_key (DOI, PMID, title, URL)
  category_code / label       from the classification
  flag_outdated_guideline_edition
                              classification flag (publication year 2015-2018)
                              restricted to guideline categories A, A* and B;
                              merge_documents.py replaces it by an edition comparison
  flag_grey_source_narrow     category F
  flag_grey_source_broad      category F or ?

Input:  ../data/classified_citations_v2.csv
Output: ../data/citations_long_v2.csv
"""
import csv, os, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data', 'intermediate')

spec = importlib.util.spec_from_file_location('ex', os.path.join(HERE, 'extract_citations.py'))
ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)

LABEL = {'A': 'applicable guideline', 'A*': 'applicable guideline (short version)',
         'B': 'other guideline', 'C': 'narrative review', 'D': 'independent evidence',
         'F': 'non-scientific source', '?': 'not classifiable'}


def main(src, dst):
    recs = list(csv.DictReader(open(src, encoding='utf-8')))
    seen, out = set(), []
    for i, r in enumerate(recs, 1):
        key = (r['rating_id'], ex.doc_key(r))
        first = 0 if key in seen else 1
        seen.add(key)
        cat = r['category']
        out.append(dict(
            citation_id='CIT2-%04d' % i,
            rating_id=r['rating_id'],
            model=r['model'],
            question_id='%s|%s' % (r['domain'], r['question_id']),
            topic_id=(int(r['domain'].split()[-1]) - 1) * 10 + int(r['question_id'][:-1]),
            source_format=r['source_format'],
            first_mention_in_answer=first,
            citation_raw_text=r['raw'],
            category_code=cat,
            category_label=LABEL[cat],
            publication_year=r['year'],
            flag_outdated_guideline_edition=1 if (r['outdated_flag'] and cat in ('A', 'A*', 'B')) else 0,
            flag_grey_source_narrow=1 if cat == 'F' else 0,
            flag_grey_source_broad=1 if cat in ('F', '?') else 0,
            author=r['author'], title=r['title'], journal=r['journal'],
            pmid=r['pmid'], doi=r['doi'], url=r['url'], url_also=r['url_also']))
    with open(dst, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    print('%d rows written: %s' % (len(out), dst))
    print('repeated mentions (first_mention_in_answer = 0): %d'
          % sum(1 for r in out if r['first_mention_in_answer'] == 0))
    print('outdated flag (year rule, guideline categories only): %d'
          % sum(r['flag_outdated_guideline_edition'] for r in out))
    print(REFERENCE)


REFERENCE = """
Reference values - a run must reproduce these:
  1475 rows; repeated mentions 33 (Open Evidence 32, GPT-5.5 1, Sonar 0; deposited table: 36, see docstring)
  outdated flag by year rule 58 (replaced in merge_documents.py by 46 via edition comparison)
"""

if __name__ == '__main__':
    s = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA, 'classified_citations_v2.csv')
    d = sys.argv[2] if len(sys.argv) > 2 else os.path.join(DATA, 'citations_long_v2.csv')
    main(s, d)
