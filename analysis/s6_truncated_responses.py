#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Supplementary Material S6 - Truncated versus complete responses, Sonar Reasoning Pro.

Produces for the manuscript:
  Limitations: "In 22 of 60 responses from Sonar Reasoning Pro the text ends
  mid-sentence ... in 18 of them the truncation fell after the answer itself had
  been given. Excluding them changes none of the endpoints for that system by more
  than four percentage points, and the only contrast that survives correction does
  not involve Sonar Reasoning Pro."
  Supplementary Material S6, three parts:
    A  where each truncated response breaks off, with the length of the prose body
    B  the endpoints for truncated, complete and all Sonar Reasoning Pro responses
    C  the pairwise contrasts for guideline reference with and without the
       truncated responses

Truncation was detected by text_completeness.py against the stored responses
(prose body ends without terminal punctuation; the appended 'Sources:' block is
not part of the model text and is stripped first). That script needs the rating
workbooks, which are not deposited. Its output, one row per truncated response,
is deposited as data/truncated_responses.csv and is the input here.

Part C repeats the sign-flip permutation over topic means from
01_topic_level_contrasts.py. When a truncated response is excluded, the topic
mean for Sonar Reasoning Pro is taken over the remaining complete response of
that topic; where both responses of a topic are truncated the topic drops out
of the contrasts involving Sonar Reasoning Pro (four topics, leaving 26). The
contrast GPT-5.5 versus Open Evidence is unaffected and is repeated unchanged so
that Holm correction runs over the same three contrasts as in Table 4.

Input
  ../data/answers_v2.csv                   180 rows, consensus ratings
  ../data/truncated_responses.csv           22 rows, truncated Sonar responses

Standard library only. Seed and permutation count fixed.
"""
import csv, os, collections, itertools, random, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ANSWERS = os.path.join(HERE, '..', 'data', 'answers_v2.csv')
TRUNCATED = os.path.join(HERE, '..', 'data', 'truncated_responses.csv')

SEED, NPERM = 20260820, 200000
ORD = {'No': 0, 'Partly': 1, 'Yes': 2}
MODELS = ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']
SONAR = 'Sonar Reasoning Pro'
SECTIONS = ['1 Direct answer', '2 Evidence and reasoning', '3 Safety note',
            '(no section recognisable)']
SECTION_LABEL = {'1 Direct answer': 'Direct answer',
                 '2 Evidence and reasoning': 'Evidence and reasoning',
                 '3 Safety note': 'Safety note',
                 '(no section recognisable)': 'no section heading recognisable'}


def topic_of(r):
    return (r['domain'], r['question_id'][:-1])


def pct(k, n):
    return 100.0 * k / n


def signflip_p(diffs, seed=SEED, nperm=NPERM):
    obs = abs(sum(diffs) / len(diffs))
    rnd, hits = random.Random(seed), 0
    for _ in range(nperm):
        s = sum(d if rnd.random() < .5 else -d for d in diffs)
        if abs(s) / len(diffs) >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (nperm + 1)


def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i])
    out, run = [0.] * len(ps), 0.
    for k, i in enumerate(o):
        run = max(run, ps[i] * (len(ps) - k))
        out[i] = min(1., run)
    return out


def main():
    answers = list(csv.DictReader(open(ANSWERS, encoding='utf-8')))
    trunc_rows = [r for r in csv.DictReader(open(TRUNCATED, encoding='utf-8'))
                  if r['model'] == SONAR]
    truncated = {(r['domain'], r['question_id']) for r in trunc_rows}
    sonar = [r for r in answers if r['model'] == SONAR]
    is_trunc = lambda r: (r['domain'], r['question_id']) in truncated

    # ------------------------------------------------------------------ Part A
    print('A  Point of truncation, %d responses (prose body without appended source list)'
          % len(trunc_rows))
    print('   %-34s %3s %10s %16s' % ('section', 'n', 'median', 'range (chars)'))
    for s in SECTIONS:
        L = sorted(int(r['chars']) for r in trunc_rows if r['truncated_in'] == s)
        if L:
            print('   %-34s %3d %10.0f %16s'
                  % (SECTION_LABEL[s], len(L), statistics.median(L), '%d-%d' % (L[0], L[-1])))
    all_len = [int(r['chars']) for r in trunc_rows]
    print('   %-34s %3d %10.0f' % ('all truncated', len(all_len), statistics.median(all_len)))
    after = sum(1 for r in trunc_rows if r['truncated_in'] != '1 Direct answer')
    print('   truncation after the direct answer section: %d of %d'
          ' (includes the one response without section headings, which states'
          ' its answer in the first sentence)' % (after, len(trunc_rows)))
    no_safety = sum(1 for r in trunc_rows if r['safety_note_present'] == 'no')
    print('   safety note section missing: %d of %d' % (no_safety, len(trunc_rows)))

    # ------------------------------------------------------------------ Part B
    groups = [('truncated', [r for r in sonar if is_trunc(r)]),
              ('complete', [r for r in sonar if not is_trunc(r)]),
              ('all', sonar)]
    metrics = [('Accuracy correct', lambda r: r['accuracy'] == 'Correct'),
               ('Guideline reference yes', lambda r: r['glr'] == 'Yes'),
               ('Guideline reference partly', lambda r: r['glr'] == 'Partly'),
               ('Guideline reference no', lambda r: r['glr'] == 'No'),
               ('Safety concern any', lambda r: r['safety'] != 'No'),
               ('Evidence quality yes', lambda r: r['evidence'] == 'Yes')]
    print('\nB  Endpoints, Sonar Reasoning Pro, n (%%)         %s'
          % '   '.join('%-16s' % ('%s (n=%d)' % (g, len(rs))) for g, rs in groups))
    for name, f in metrics:
        cells = ['%2d (%5.1f)' % (sum(map(f, rs)), pct(sum(map(f, rs)), len(rs))) for _, rs in groups]
        print('   %-40s %s' % (name, '   '.join('%-16s' % c for c in cells)))
    cells = ['%.2f' % (sum(ORD[r['glr']] for r in rs) / len(rs)) for _, rs in groups]
    print('   %-40s %s' % ('Mean ordinal guideline reference', '   '.join('%-16s' % c for c in cells)))
    # largest shift in percentage points between complete-only and all
    shifts = []
    for name, f in metrics:
        a = pct(sum(map(f, groups[2][1])), 60)
        c = pct(sum(map(f, groups[1][1])), len(groups[1][1]))
        shifts.append((abs(a - c), name))
    print('   largest shift, complete-only versus all: %.1f pp (%s)' % max(shifts))

    # ------------------------------------------------------------------ Part C
    per_topic = collections.defaultdict(list)
    for r in answers:
        per_topic[(r['model'], topic_of(r))].append(r)
    topics = sorted({t for _, t in per_topic}, key=lambda x: (x[0], int(x[1])))
    both_trunc = [t for t in topics if all(is_trunc(r) for r in per_topic[(SONAR, t)])]

    def value(r, scale):
        return ORD[r['glr']] if scale == 'ordinal' else float(r['glr'] == 'Yes')

    def topic_mean(m, t, scale, exclude):
        rs = [r for r in per_topic[(m, t)] if not (exclude and m == SONAR and is_trunc(r))]
        return sum(value(r, scale) for r in rs) / len(rs) if rs else None

    print('\nC  Pairwise contrasts for guideline reference, sign-flip permutation over'
          ' topic means, Holm within scale')
    print('   topics with both Sonar Reasoning Pro responses truncated: %d (%s)'
          % (len(both_trunc), ', '.join('%s/%s' % t for t in both_trunc)))
    results = {}
    for exclude, label in [(False, 'all responses'), (True, 'truncated Sonar responses excluded')]:
        for scale, sname in [('binary', 'exact reference'), ('ordinal', 'three-level scale')]:
            raw, names, ns, effs = [], [], [], []
            for a, b in [('GPT-5.5', 'Open Evidence'), ('GPT-5.5', SONAR), (SONAR, 'Open Evidence')]:
                d = []
                for t in topics:
                    x, y = topic_mean(a, t, scale, exclude), topic_mean(b, t, scale, exclude)
                    if x is None or y is None:
                        continue
                    d.append(x - y)
                raw.append(signflip_p(d)); names.append('%s vs %s' % (a, b))
                ns.append(len(d)); effs.append(sum(d) / len(d))
            adj = holm(raw)
            results[(exclude, scale)] = adj
            print('   %s, %s' % (label, sname))
            print('   %-40s %6s %9s %8s %8s' % ('contrast', 'topics', 'effect', 'p raw', 'Holm'))
            for n, k, e, p, h in zip(names, ns, effs, raw, adj):
                ev = '%+.1f pp' % (100 * e) if scale == 'binary' else '%+.2f' % e
                print('   %-40s %6d %9s %8.4f %8.4f' % (n, k, ev, p, h))
    print(REFERENCE)


REFERENCE = """
Reference values - a run must reproduce these:
  A  Direct answer 4 (median 784 chars), Evidence and reasoning 15 (2740),
     Safety note 2 (4384), no section heading 1 (638); all 22, median 2344.
     After the direct answer: 18 of 22. Safety note missing: 20 of 22.
  B  truncated / complete / all (n = 22 / 38 / 60), %:
     accuracy correct        81.8 / 76.3 / 78.3
     guideline reference yes 45.5 / 55.3 / 51.7
     guideline reference no  22.7 / 23.7 / 23.3
     safety concern           4.5 /  0.0 /  1.7
     evidence quality yes    72.7 / 78.9 / 76.7
     mean ordinal reference  1.23 / 1.32 / 1.28
     largest shift complete-only vs all: 3.9 pp
  C  Holm p, order GPT vs OE / GPT vs Sonar / Sonar vs OE
     exact reference,   all responses         0.038 / 0.082 / 0.155   (= Table 4)
     exact reference,   truncated excluded    0.038 / 0.094 / 0.092   (26 topics for Sonar)
     three-level scale, all responses         0.009 / 0.001 / 0.489   (= Table 4)
     three-level scale, truncated excluded    0.014 / 0.014 / 0.211
"""

if __name__ == '__main__':
    main()
