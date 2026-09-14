# -*- coding: utf-8 -*-
"""Supplementary analyses: topic structure, domain heterogeneity, grade of recommendation, effect sizes.

Produces for the manuscript:
  Methods 2.6      intraclass correlation of the two questions of a topic (0.752)
  Results 3.7      model-by-domain heterogeneity and its pairwise decomposition
  Results 3.6      effect of the grade of recommendation per system (Holm p 0.0045 / 0.21 / 0.61)
  Table 4          Cliff's delta point estimates (intervals: 02_cliffs_delta.py)
  Results 3.1      knowledge versus case questions, odds ratio per system

Input: a table with one row per response and the columns
    domain          'Domain 1' | 'Domain 2' | 'Domain 3'
    question_id     '1a' ... '10b'
    model           'Open Evidence' | 'GPT-5.5' | 'Sonar Reasoning Pro'
    glr             'No' | 'Partly' | 'Yes'     (consensus rating, guideline reference)
    accuracy        'Correct' | 'Partially correct' | 'Incorrect'
i.e. ../data/answers_v2.csv, 180 rows.

The 30 SIGN grades are hard-coded below and match data/items_master.csv. Topic
assignment needs no data: questions '3a' and '3b' of the same domain form one topic.

Seed and number of permutations fixed. Standard library only.
"""
import csv, os, random, itertools, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ANSWERS = os.path.join(HERE, '..', 'data', 'answers_v2.csv')

SEED, N_PERM = 20260812, 200000
DOM = ['Domain 1', 'Domain 2', 'Domain 3']
MODELS = ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']
ORD = {'No': 0, 'Partly': 1, 'Yes': 2}

# The 30 source recommendations with their SIGN grade of recommendation, read from the
# full texts of the three ESPEN guidelines, cross-checked three times, confirmed 12 Aug 2026.
# Key: (domain, topic number). The grade applies to both questions of the topic.
SIGN_GRADE = {
    ('Domain 1','1'):'GPP',  ('Domain 1','2'):'B',   ('Domain 1','3'):'GPP', ('Domain 1','4'):'GPP',
    ('Domain 1','5'):'A',    ('Domain 1','6'):'B',   ('Domain 1','7'):'GPP', ('Domain 1','8'):'GPP',
    ('Domain 1','9'):'B',    ('Domain 1','10'):'B',
    ('Domain 2','1'):'GPP',  ('Domain 2','2'):'GPP', ('Domain 2','3'):'A',   ('Domain 2','4'):'GPP',
    ('Domain 2','5'):'GPP',  ('Domain 2','6'):'GPP', ('Domain 2','7'):'A',   ('Domain 2','8'):'A',
    ('Domain 2','9'):'A',    ('Domain 2','10'):'A',
    ('Domain 3','1'):'0',    ('Domain 3','2'):'GPP', ('Domain 3','3'):'A',   ('Domain 3','4'):'GPP',
    ('Domain 3','5'):'GPP',  ('Domain 3','6'):'GPP', ('Domain 3','7'):'GPP', ('Domain 3','8'):'GPP',
    ('Domain 3','9'):'GPP',  ('Domain 3','10'):'GPP',
}
# Two special cases, for the record:
#   Domain 2 / 10  Geriatrics Rec 12 carries A/GPP (A in institutions, GPP at home).
#                  Our questions name no setting. Rule: first grade listed, i.e. A.
#   Domain 1 / 7   derives from the commentary to Dementia Rec 9, not from the
#                  recommendation sentence. Grade is that of Rec 9.


def load(path):
    """Reads the 180 response rows and forms topic means per system."""
    val = collections.defaultdict(list)
    for r in csv.DictReader(open(path)):
        topic = (r['domain'], r['question_id'][:-1])       # '3a' -> topic '3'
        val[(r['model'], topic)].append(ORD[r['glr']])
    topics = sorted({t for (_, t) in val}, key=lambda t: (t[0], int(t[1])))
    return topics, {k: sum(v) / len(v) for k, v in val.items()}


def one_way_F(values, groups):
    gm = sum(values) / len(values)
    G = collections.defaultdict(list)
    for v, g in zip(values, groups):
        G[g].append(v)
    k, n = len(G), len(values)
    ssb = sum(len(v) * (sum(v) / len(v) - gm) ** 2 for v in G.values())
    ssw = sum(sum((x - sum(v) / len(v)) ** 2 for x in v) for v in G.values())
    return (ssb / (k - 1)) / (ssw / (n - k)) if ssw else float('inf')


def perm_p(stat_fn, labels, n_perm=N_PERM, seed=SEED):
    obs = stat_fn(labels)
    rnd, lab, hits = random.Random(seed), list(labels), 0
    for _ in range(n_perm):
        rnd.shuffle(lab)
        if stat_fn(lab) >= obs - 1e-12:
            hits += 1
    return obs, (hits + 1) / (n_perm + 1)


def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i])
    out, run = [0.0] * len(ps), 0.0
    for k, i in enumerate(o):
        run = max(run, ps[i] * (len(ps) - k))
        out[i] = min(1.0, run)
    return out


def run(path=ANSWERS):
    topics, val = load(path)
    dom = [t[0] for t in topics]
    print('%d topics, %d questions\n' % (len(topics), 2 * len(topics)))

    # 1  Are the two questions of a topic independent? No.
    pairs = []
    raw = collections.defaultdict(list)
    for r in csv.DictReader(open(path)):
        raw[(r['model'], (r['domain'], r['question_id'][:-1]), r['question_id'][-1])] = ORD[r['glr']]
    for t in topics:
        pairs.append((raw[('GPT-5.5', t, 'a')] - raw[('Open Evidence', t, 'a')],
                      raw[('GPT-5.5', t, 'b')] - raw[('Open Evidence', t, 'b')]))
    flat = [x for p in pairs for x in p]
    gm = sum(flat) / len(flat)
    msb = 2 * sum(((a + b) / 2 - gm) ** 2 for a, b in pairs) / (len(pairs) - 1)
    msw = sum((a - (a + b) / 2) ** 2 + (b - (a + b) / 2) ** 2 for a, b in pairs) / len(pairs)
    print('1  ICC of the question pairs (GPT minus Open Evidence): %.3f' % ((msb - msw) / (msb + msw)))
    print('   -> the 60 questions are 30 units, not 60\n')

    # 2  System x domain, omnibus over all three systems
    def interaction_F(labels):
        L = dict(zip(topics, labels))
        cells = {(m, d): [val[(m, t)] for t in topics if L[t] == d] for m in MODELS for d in DOM}
        gm_ = sum(val[(m, t)] for m in MODELS for t in topics) / (3 * len(topics))
        mm = {m: sum(val[(m, t)] for t in topics) / len(topics) for m in MODELS}
        dm = {d: sum(v for m in MODELS for v in cells[(m, d)]) /
                 sum(len(cells[(m, d)]) for m in MODELS) for d in DOM}
        ssi = ssw_ = 0.0
        for m in MODELS:
            for d in DOM:
                v = cells[(m, d)]
                if not v:
                    continue
                cm = sum(v) / len(v)
                ssi += len(v) * (cm - mm[m] - dm[d] + gm_) ** 2
                ssw_ += sum((x - cm) ** 2 for x in v)
        return (ssi / 4) / (ssw_ / (3 * len(topics) - 9)) if ssw_ else float('inf')

    F, p = perm_p(interaction_F, dom)
    print('2  Omnibus system x domain:  F = %.3f  p = %.4f' % (F, p))

    # 3  ... then pairwise, unadjusted (Fisher's protected LSD, valid for three groups)
    ps = []
    for a, b in itertools.combinations(MODELS, 2):
        d_ = [val[(a, t)] - val[(b, t)] for t in topics]
        F, p = perm_p(lambda lab: one_way_F(d_, lab), dom)
        ps.append(p)
        print('   %-14s vs %-20s F = %6.3f  p = %.4f' % (a, b, F, p))
    print('   for information, Holm over three pairs: %s\n' % '  '.join('%.3f' % v for v in holm(ps)))

    # 4  Grade of recommendation: evidence-graded (A/B/0) versus good practice point (GPP)
    grade0 = ['GPP' if SIGN_GRADE[t] == 'GPP' else 'ev' for t in topics]
    ps = []
    for m in MODELS:
        def stat(labels):
            L = dict(zip(topics, labels))
            s = 0.0
            for d in DOM:
                idx = [t for t in topics if t[0] == d]
                A = [val[(m, t)] for t in idx if L[t] == 'ev']
                B = [val[(m, t)] for t in idx if L[t] == 'GPP']
                if A and B:
                    s += sum(A) / len(A) - sum(B) / len(B)
            return abs(s)
        # Permute within domains so that the domain effect is not measured along with it
        obs = stat(grade0)
        rnd, hits = random.Random(SEED), 0
        for _ in range(50000):
            lab = list(grade0)
            for d in DOM:
                idx = [i for i, t in enumerate(topics) if t[0] == d]
                sub = [lab[i] for i in idx]
                rnd.shuffle(sub)
                for i, v in zip(idx, sub):
                    lab[i] = v
            if stat(lab) >= obs - 1e-12:
                hits += 1
        ps.append((hits + 1) / 50001)
        ev = [val[(m, t)] for t in topics if SIGN_GRADE[t] != 'GPP']
        gp = [val[(m, t)] for t in topics if SIGN_GRADE[t] == 'GPP']
        print('4  %-20s evidence-graded %.2f  GPP %.2f  p = %.4f'
              % (m, sum(ev) / len(ev), sum(gp) / len(gp), ps[-1]))
    print('   Holm over the three systems: %s' % '  '.join('%.4f' % v for v in holm(ps)))


def effektstaerken(path=ANSWERS):
    """Cliff's delta for the three pairwise contrasts and the odds ratio knowledge versus case questions."""
    rows = list(csv.DictReader(open(path)))
    glr = {(r['model'], r['domain'], r['question_id']): ORD[r['glr']] for r in rows}
    acc = {(r['model'], r['domain'], r['question_id']): r['accuracy'] for r in rows}
    qs = sorted({(r['domain'], r['question_id']) for r in rows})

    def cliff(x, y):
        gt = sum(1 for a in x for b in y if a > b)
        lt = sum(1 for a in x for b in y if a < b)
        return (gt - lt) / (len(x) * len(y))

    print('\n5  Cliff\'s delta, three-level guideline reference (BCa intervals: 02_cliffs_delta.py)')
    for a, b in itertools.combinations(MODELS, 2):
        d = cliff([glr[(b,) + q] for q in qs], [glr[(a,) + q] for q in qs])
        print('   %-14s vs %-20s delta = %+.3f' % (b, a, d))

    print('\n6  Knowledge versus case questions, odds ratio per system')
    print('   No response was rated "Incorrect", so the scale is effectively binary;')
    print('   the ordered-logit odds ratio then equals the cross-product of the 2x2 table.')
    for m in MODELS:
        k_ok = sum(1 for q in qs if q[1].endswith('a') and acc[(m,) + q] == 'Correct')
        k_no = sum(1 for q in qs if q[1].endswith('a') and acc[(m,) + q] != 'Correct')
        c_ok = sum(1 for q in qs if q[1].endswith('b') and acc[(m,) + q] == 'Correct')
        c_no = sum(1 for q in qs if q[1].endswith('b') and acc[(m,) + q] != 'Correct')
        orr = (k_ok * c_no) / (k_no * c_ok) if k_no * c_ok else float('inf')
        print('   %-20s knowledge %2d/%d correct, case %2d/%d  ->  OR = %.2f'
              % (m, k_ok, k_ok + k_no, c_ok, c_ok + c_no, orr))


REFERENZWERTE = """
Reference values - a run must reproduce these:
  1  ICC of the question pairs                 0.752
  2  Omnibus system x domain                   F 3.103   p 0.026
  3  Pairwise contrasts, topic level           0.023 / 0.051 / 0.761
     for information, Holm over three pairs    0.069 / 0.101 / 0.761
  4  Grade of recommendation, Open Evidence    0.71 vs 1.47   Holm p 0.0045
     GPT-5.5 0.208, Sonar Reasoning Pro 0.610
  5  Cliff's delta  GPT vs OE +0.391, GPT vs Sonar +0.241, Sonar vs OE +0.104
     (confidence intervals: 02_cliffs_delta.py)
  6  Odds ratio question type   OE 2.15, GPT-5.5 5.80, Sonar 0.36; none significant.
     Rests on 6, 6 and 13 not fully correct responses; intervals correspondingly wide.
"""


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else ANSWERS
    run(path)
    effektstaerken(path)
    print(REFERENZWERTE)
