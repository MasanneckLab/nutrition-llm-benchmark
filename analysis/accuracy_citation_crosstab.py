#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-tabulation of accuracy with citation behaviour.

Produces for the manuscript:
  Results 3.1   "Of the 25 responses that were not fully correct, the applicable
                guideline was identifiable in ten, and eight cited an earlier
                edition of a guideline, five of them from GPT-5.5."
  Discussion    "GPT-5.5 cited the 2018 edition accurately and reproduced its earlier
                figure, one of five of its responses in which an earlier edition went
                together with a rating of partially correct." The five are GPT-5.5's
                share of the eight; the response in question is NUTR-D2-8B-03.

Definitions
  not fully correct       consensus_accuracy is not 'Correct'. All 25 such responses
                          carry 'Partially correct'; none was rated 'Incorrect', so
                          "not fully correct" and "partially correct" are the same set.
  guideline identifiable  consensus_guideline_reference is 'Yes'.
  earlier edition         at least one citation of the response carries
                          flag_outdated_guideline_edition = 1. The flag compares the
                          cited edition with the current one (merge_documents.py); it
                          covers the categories A, A* and B, i.e. any guideline and not
                          only the one of the item.

All three counts refer to the same 25 responses; the two subsets are not nested
inside one another. Of the 25, ten have an identifiable guideline and eight cite an
earlier edition, and these two groups overlap in five responses. The intersection is
printed below as well, so that the Results sentence cannot be misread as nesting them.

Known under-detection of the flag: four Sonar citations of the 2018 polymorbidity
guideline are linked via nespen.nl instead of espen.org, where the edition cannot be
read off (table5_citation_sources.py). None of the four belongs to a response in this
table, so the counts here are unaffected.

Input
  ../data/ratings_raters.csv     180 rows, consensus ratings
  ../data/citations_long_v3.csv  1,462 citations with the edition flag, joined by rating_id

Standard library only.
"""
import csv, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
RATERS = os.path.join(HERE, '..', 'data', 'ratings_raters.csv')
CITATIONS = os.path.join(HERE, '..', 'data', 'citations_long_v3.csv')

ORDER = ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']


def by_system(rs):
    c = collections.Counter(r['model'] for r in rs)
    return '  '.join('%s %d' % (m.split()[0], c[m]) for m in ORDER)


def main():
    ratings = list(csv.DictReader(open(RATERS, encoding='utf-8')))
    outdated = collections.defaultdict(bool)
    for c in csv.DictReader(open(CITATIONS, encoding='utf-8')):
        if c['flag_outdated_guideline_edition'] == '1':
            outdated[c['rating_id']] = True

    not_correct = [r for r in ratings if r['consensus_accuracy'] != 'Correct']
    identifiable = [r for r in not_correct if r['consensus_guideline_reference'] == 'Yes']
    earlier = [r for r in not_correct if outdated[r['rating_id']]]
    both = [r for r in identifiable if outdated[r['rating_id']]]

    print('Responses that were not fully correct, and what they cited')
    print('  %-46s %3d    %s' % ('not fully correct', len(not_correct), by_system(not_correct)))
    print('  %-46s %3d    %s' % ('  of these, applicable guideline identifiable',
                                 len(identifiable), by_system(identifiable)))
    print('  %-46s %3d    %s' % ('  of these, citing an earlier edition',
                                 len(earlier), by_system(earlier)))
    print('  %-46s %3d    %s' % ('  in both groups at once', len(both), by_system(both)))

    grades = collections.Counter(r['consensus_accuracy'] for r in not_correct)
    print('\n  accuracy ratings among the %d: %s' % (len(not_correct), dict(grades)))
    print('  responses citing an earlier edition, by system and rating id:')
    for m in ORDER:
        ids = sorted(r['rating_id'] for r in earlier if r['model'] == m)
        print('     %-22s %d   %s' % (m, len(ids), ', '.join(ids) if ids else '-'))
    print(REFERENCE)


REFERENCE = """
Reference values - a run must reproduce these:
  not fully correct                              25   Open Evidence 6   GPT-5.5 6   Sonar 13
  of these, applicable guideline identifiable    10   Open Evidence 1   GPT-5.5 4   Sonar  5
  of these, citing an earlier edition             8   Open Evidence 0   GPT-5.5 5   Sonar  3
  in both groups at once                          5   Open Evidence 0   GPT-5.5 3   Sonar  2
  all 25 carry 'Partially correct'; none was rated 'Incorrect'
"""

if __name__ == '__main__':
    main()
