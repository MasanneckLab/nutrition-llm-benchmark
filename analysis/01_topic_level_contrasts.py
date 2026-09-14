# -*- coding: utf-8 -*-
"""01 - Topic-robust pairwise contrasts on the primary endpoint (guideline reference).

Produces for the manuscript:
  Table 4, columns "Exact reference, P value" and "Three-level scale, P value":
    GPT-5.5 vs Open Evidence, three-level      Holm p = 0.009
    GPT-5.5 vs Open Evidence, exact            Holm p = 0.038
    GPT-5.5 vs Sonar Reasoning Pro, three-level Holm p = 0.001
    Sonar Reasoning Pro vs Open Evidence       not significant

Background: the knowledge question and the case question of a topic derive from
the same ESPEN source recommendation. The 60 questions are 30 topics. Tests run
over the 30 paired topic means with sign-flip permutation.

Input:  ../data/answers_v2.csv  (180 rows; domain, question_id, model, glr, accuracy, safety, evidence)
Seed and number of permutations fixed. Standard library only.
"""
import csv, os, collections, itertools, random

HERE = os.path.dirname(os.path.abspath(__file__))
ANSWERS = os.path.join(HERE, '..', 'data', 'answers_v2.csv')

SEED, NPERM = 20260820, 200000
ORD = {'No': 0, 'Partly': 1, 'Yes': 2}
MODELS = ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']

rows = list(csv.DictReader(open(ANSWERS, encoding='utf-8')))
item, topic = {}, collections.defaultdict(list)
for r in rows:
    t = (r['domain'], r['question_id'][:-1])
    item[(r['model'], r['domain'], r['question_id'])] = r
    topic[(r['model'], t)].append(r)
topics = sorted({t for (_, t) in topic}, key=lambda x: (x[0], int(x[1])))
questions = sorted({(r['domain'], r['question_id']) for r in rows})


def val(r, endpoint):
    return ORD[r['glr']] if endpoint == 'ordinal' else (1.0 if r['glr'] == 'Yes' else 0.0)


def topic_mean(m, t, endpoint):
    v = [val(r, endpoint) for r in topic[(m, t)]]
    return sum(v) / len(v)


def signflip_p(diffs, seed=SEED, nperm=NPERM):
    """Two-sided permutation test for paired differences."""
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


for endpoint, label in [('ordinal', 'Three-level guideline reference (0-2)'),
                        ('binary', 'Exact guideline reference (yes vs not yes)')]:
    print('\n=== %s' % label)
    print('%-38s %10s %10s %10s' % ('Contrast', 'Difference', 'p topic', 'Holm'))
    raw, diffs, names = [], [], []
    for a, b in itertools.combinations(MODELS, 2):
        dt = [topic_mean(a, t, endpoint) - topic_mean(b, t, endpoint) for t in topics]
        raw.append(signflip_p(dt)); diffs.append(dt); names.append('%s vs %s' % (a, b))
    h = holm(raw)
    for k, n in enumerate(names):
        d = sum(diffs[k]) / len(diffs[k])
        dv, unit = (d * 100, ' pp') if endpoint == 'binary' else (d, '')
        print('%-38s %+9.1f%s %10.4f %10.4f' % (n, dv, unit, raw[k], h[k]))

REFERENCE = """
Reference values - a run must reproduce these:
  three-level  OE vs GPT   -0.50     p 0.0046   Holm 0.0091
               OE vs Sonar -0.12     p 0.4890   Holm 0.4890
               GPT vs Sonar +0.40    p 0.0005   Holm 0.0014
  exact        OE vs GPT   -33.3 pp  p 0.0127   Holm 0.0381
               OE vs Sonar -16.7 pp  p 0.1554   Holm 0.1554
               GPT vs Sonar +16.7 pp p 0.0409   Holm 0.0818
"""
print(REFERENCE)
