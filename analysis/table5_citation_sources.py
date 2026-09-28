# -*- coding: utf-8 -*-
"""Table 5 - Composition of the cited sources.

Builds the table from citations_long_v3.csv, the category revision and the in-text
assignment. Percentages at citation level, frequencies at response level with
denominator 60.

Row definitions: citations per response; responses citing the applicable guideline
(category A or A*); responses combining two or more guidelines; responses citing an
earlier guideline edition (flag over categories A, A* and B, see merge_documents.py);
non-scientific sources (category F after revise_categories.py).

Only citations that the response actually invokes in its running text are counted
(column invoked_in_text from citations_in_text.csv). Reason: for Sonar Reasoning Pro
the appended URL list does not come from the model but from the citations field of
the Perplexity API. Counting it measures the hit list of a search engine rather than
the citation behaviour. The rule applies uniformly to all three systems; for GPT-5.5
it has no effect because every citation is in the running text.

The analysis over all extracted citations is printed below as a sensitivity
analysis (Supplementary Material S5).

Usage:
    python3 table5_citation_sources.py [../data/citations_long_v3.csv] [../data/category_revision.csv]
                                       [../data/citations_in_text.csv]

Prerequisite: revise_categories.py and in_text_citations.py have been run.
Standard library only.
"""
import csv, sys, os, re, collections, statistics

MODELS = ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']
APPL = {'A', 'A*'}          # guideline applicable to the item, incl. short version
GUIDE = APPL | {'B'}        # any guideline
W = '%-52s %14s %14s %14s'


def blob(r):
    return ((r['title'] or '') + ' ' + (r['url'] or '') + ' ' + (r['citation_raw_text'] or '')).lower()


def vorgaengerausgabe(r):
    """Does the response cite an earlier, since replaced, edition of a guideline?

    Authoritative is the column flag_outdated_guideline_edition from
    merge_documents.py. Counted over the categories A, A* and B, i.e. over any
    guideline and not only the one of the item: whether a system cites a replaced
    edition is of interest independently of which guideline underlies the
    question. The narrower count over A and A* only would give 0 / 36 / 6
    instead of 0 / 38 / 8.

    Known under-detection: the flag requires that the edition can be read from
    the source. For four Sonar citations of the 2018 polymorbidity guideline that
    are linked via nespen.nl instead of espen.org this fails
    (NUTR-D1-2B-03, NUTR-D1-10B-01, NUTR-D2-8A-03, NUTR-D2-9A-01). Sonar is thus
    in fact at 11 rather than 8 of 60 responses. The table value follows this
    definition; the under-detection belongs in the Methods section.
    """
    return r['flag_outdated_guideline_edition'] == '1'


def dokument(r):
    """Coarse document identity for the question whether several guidelines were combined."""
    t = (r['title'] or '').strip()
    if t:
        return ('T', t[:70].lower())
    u = (r['url'] or '').strip()
    if u:
        u = re.sub(r'[?#].*$', '', u)
        u = re.sub(r'^https?://(www\.)?', '', u).rstrip('/')
        return ('U', u.lower())
    return ('R', (r['citation_raw_text'] or '')[:70].lower())


def main(quelle, revision, belege):
    rev = {r['citation_id']: r for r in csv.DictReader(open(revision, encoding='utf-8'))}
    beleg = {r['citation_id']: r['invoked_in_text'] == '1'
             for r in csv.DictReader(open(belege, encoding='utf-8'))}
    alle = list(csv.DictReader(open(quelle, encoding='utf-8')))
    for r in alle:
        r['kat'] = rev[r['citation_id']]['category_new']
        r['komm'] = rev[r['citation_id']]['commercial']
        r['beleg'] = beleg[r['citation_id']]
    rows = [r for r in alle if r['beleg']]
    by = {m: [r for r in rows if r['model'] == m] for m in MODELS}

    def zeile(label, fn):
        print(W % (label, *[fn(m) for m in MODELS]))

    def anteil(ks):
        return lambda m: '%.1f' % (100 * sum(1 for r in by[m] if r['kat'] in ks) / len(by[m]))

    def antworten(pred):
        return lambda m: '%d' % len({r['rating_id'] for r in by[m] if pred(r)})

    print(W % ('', *MODELS))
    zeile('Citations, total', lambda m: len(by[m]))

    def median_je_antwort(m):
        c = collections.Counter(r['rating_id'] for r in by[m])
        n = [c[q] for q in c] + [0] * (60 - len(c))
        return '%.0f' % statistics.median(n)
    zeile('Citations per response, median', median_je_antwort)

    print()
    print('%-52s %s' % ('Source category, % of citations', ''))
    zeile('  Applicable guideline', anteil(APPL))
    zeile('  Other clinical practice guideline', anteil({'B'}))
    zeile('  Narrative review', anteil({'C'}))
    zeile('  Independent evidence', anteil({'D'}))
    zeile('  Non-scientific source', anteil({'F'}))

    print()
    print('%-52s %s' % ('Response level, n of 60', ''))
    zeile('  Citing the applicable guideline', antworten(lambda r: r['kat'] in APPL))
    # definition: any guideline, not only the one of the item.
    zeile('  Citing an earlier edition', antworten(lambda r: vorgaengerausgabe(r) and r['kat'] in GUIDE))
    zeile('  With at least one non-scientific source', antworten(lambda r: r['kat'] == 'F'))

    print()
    print('%-52s %s' % ('For information, not part of Table 5', ''))
    zeile('  Citing any clinical practice guideline', antworten(lambda r: r['kat'] in GUIDE))

    def kombiniert(m):
        d = collections.defaultdict(set)
        for r in by[m]:
            if r['kat'] in GUIDE:
                d[r['rating_id']].add(dokument(r))
        return sum(1 for q in d if len(d[q]) >= 2)
    zeile('  Combining two or more guidelines', kombiniert)
    zeile('  With at least one commercial source', antworten(lambda r: r['komm'] == '1'))

    print()
    print('%-52s %s' % ('Sensitivity analysis (S5): all extracted citations', ''))
    byall = {m: [r for r in alle if r['model'] == m] for m in MODELS}
    print(W % ('  Citations', *[len(byall[m]) for m in MODELS]))
    print(W % ('  Non-scientific, %',
               *['%.1f' % (100 * sum(1 for r in byall[m] if r['kat'] == 'F') / len(byall[m])) for m in MODELS]))
    print(W % ('  Responses with a non-scientific source',
               *['%d' % len({r['rating_id'] for r in byall[m] if r['kat'] == 'F'}) for m in MODELS]))

    print()
    print('Reference values - a run must reproduce these:')
    print('  Citations invoked          290 / 168 / 400')
    print('  Median per response          5 /   3 /   6')
    print('  Applicable guideline, %    0.0 / 32.1 / 8.8')
    print('  Other guideline, %        27.2 / 28.6 / 14.5')
    print('  Narrative review, %       25.2 /  0.0 /  0.0')
    print('  Independent evidence, %   47.6 / 39.3 / 54.0')
    print('  Non-scientific, %          0.0 /  0.0 / 22.8')
    print('  Responses citing the applicable guideline   0 / 52 / 28  of 60')
    print('  Responses citing an earlier edition         0 / 38 /  8  of 60  (under-detection, see docstring)')
    print('  Responses with a non-scientific source      0 /  0 / 33  of 60')
    print('  Sensitivity, all citations  431 / 168 / 863; non-scientific 0.0 / 0.0 / 38.6 %; responses 0 / 0 / 56')


if __name__ == '__main__':
    q = sys.argv[1] if len(sys.argv) > 1 else os.path.join('..', 'data', 'citations_long_v3.csv')
    v = sys.argv[2] if len(sys.argv) > 2 else os.path.join('..', 'data', 'category_revision.csv')
    b = sys.argv[3] if len(sys.argv) > 3 else os.path.join('..', 'data', 'citations_in_text.csv')
    main(q, v, b)
