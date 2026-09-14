#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reproduction of Table 3, the omnibus and McNemar tests, inter-rater agreement and the domain effect.

Produces for the manuscript:
  Table 3          counts, percentages and Wilson intervals per system; omnibus p values
  Results 3.1      accuracy: omnibus marginally significant, no pairwise contrast after Holm
  Results 3.4      evidence quality: Holm-adjusted McNemar p = 0.003, 0.013, 0.375
  Results 3.2      safety concern: no difference between systems
  Results 3.1      inter-rater agreement, Cohen's kappa and Gwet's AC1 per dimension
                   (AC1 over the categories actually assigned)
  Results 3.7      marginal domain effect on exact guideline reference (pseudo-F 5.005)
                   and accuracy (pseudo-F 0.565, p = 0.60)

Every statistic is written out explicitly rather than taken from a library, so that
each step can be followed against the Methods section, and the script runs without
SciPy. Only numpy is required.

Input
  ../data/answers_v2.csv      180 rows, consensus ratings, four endpoints
  ../data/ratings_raters.csv  180 rows, both raters and the consensus

Usage
  python3 reproduce_statistics.py

Not included here: the topic-level sign-flip contrasts (01_topic_level_contrasts.py),
Cliff's delta with bootstrap intervals (02_cliffs_delta.py), the model-by-domain
heterogeneity and the grade effect (supplementary_analyses.py).

An earlier version of this script read the rating workbooks directly; it is kept in
archive/ for the record.
"""
import sys, os, math, csv, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ANSWERS = os.path.join(HERE, '..', 'data', 'answers_v2.csv')
RATERS = os.path.join(HERE, '..', 'data', 'ratings_raters.csv')

# ----------------------------------------------------------------- distributions

def chi2_sf_df2(x):
    """Survival function of the chi-square distribution with 2 degrees of freedom.
    For df = 2 the closed form is P(X > x) = exp(-x/2)."""
    return math.exp(-x / 2.0)


def normal_sf(z):
    """Survival function of the standard normal distribution via the error function."""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def binom_two_sided_exact(n01, n10):
    """Exact two-sided binomial test over the discordant pairs (McNemar)."""
    n = n01 + n10
    if n == 0:
        return 1.0
    k = min(n01, n10)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2.0 ** n
    return min(1.0, 2.0 * tail)


# ----------------------------------------------------------------- tests

def cochran_q(m):
    """Cochran's Q for k paired binary measurements on n cases. df = k-1."""
    n, k = m.shape
    Tj = m.sum(axis=0)          # column sums, per system
    Li = m.sum(axis=1)          # row sums, per question
    N = m.sum()
    num = (k - 1) * (k * (Tj ** 2).sum() - N ** 2)
    den = k * N - (Li ** 2).sum()
    return num / den if den else float('nan')


def _rank_with_ties(row):
    """Mean ranks within a row."""
    vals, inv, cnt = np.unique(row, return_inverse=True, return_counts=True)
    starts = np.concatenate(([0], np.cumsum(cnt)))[:-1]
    avg = (starts + 1 + starts + cnt) / 2.0
    return avg[inv]


def friedman(m):
    """Friedman statistic with tie correction. df = k-1."""
    n, k = m.shape
    R = np.vstack([_rank_with_ties(m[i]) for i in range(n)])
    Rj = R.sum(axis=0)
    stat = 12.0 / (n * k * (k + 1)) * (Rj ** 2).sum() - 3 * n * (k + 1)
    ties = 0
    for i in range(n):
        _, cnt = np.unique(m[i], return_counts=True)
        ties += sum(c ** 3 - c for c in cnt)
    corr = 1 - ties / (n * (k ** 3 - k))
    return stat / corr if corr > 0 else stat


def mcnemar_exact(a, b):
    """Exact McNemar test for two paired binary vectors."""
    n10 = int(((a == 1) & (b == 0)).sum())
    n01 = int(((a == 0) & (b == 1)).sum())
    return n10, n01, binom_two_sided_exact(n01, n10)


def holm(pvals):
    """Holm-Bonferroni correction within one family of tests."""
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    out = [0.0] * n
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, pvals[i] * (n - rank))
        out[i] = min(1.0, running)
    return out


def wilson_ci(k, n, z=1.959963984540054):
    """Wilson score interval for a proportion, in percent."""
    if n == 0:
        return (float('nan'), float('nan'))
    p = k / n
    d = 1 + z ** 2 / n
    c = (p + z ** 2 / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / d
    return (100 * (c - h), 100 * (c + h))


def cohen_kappa(x, y, cats):
    """Cohen's kappa for two raters, independent first ratings."""
    n = len(x)
    po = sum(1 for i in range(n) if x[i] == y[i]) / n
    cx = collections.Counter(x)
    cy = collections.Counter(y)
    pe = sum((cx[c] / n) * (cy[c] / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else float('nan')


def gwet_ac1(x, y, cats):
    """Gwet's AC1. More robust than kappa under strongly skewed marginals."""
    n = len(x)
    q = len(cats)
    po = sum(1 for i in range(n) if x[i] == y[i]) / n
    pi = {c: (collections.Counter(x)[c] + collections.Counter(y)[c]) / (2 * n) for c in cats}
    pe = sum(pi[c] * (1 - pi[c]) for c in cats) / (q - 1)
    return (po - pe) / (1 - pe) if pe < 1 else float('nan')


def permutation_domain_effect(values_by_question, domain_labels, n_perm=200000, seed=20260712):
    """Permutation test of the marginal domain effect at question level.

    Values are averaged over the three systems per question, then the domain
    labels are permuted. The test statistic is a pseudo-F from the sums of
    squares between and within domains.
    """
    v = np.asarray(values_by_question, float)
    lab = np.asarray(domain_labels)
    groups = np.unique(lab)

    def pseudo_f(labels):
        gm = v.mean()
        ssb = sum((labels == g).sum() * (v[labels == g].mean() - gm) ** 2 for g in groups)
        ssw = sum(((v[labels == g] - v[labels == g].mean()) ** 2).sum() for g in groups)
        dfb, dfw = len(groups) - 1, len(v) - len(groups)
        return (ssb / dfb) / (ssw / dfw) if ssw > 0 else float('inf')

    obs = pseudo_f(lab)
    rng = np.random.default_rng(seed)
    perm = lab.copy()
    count = 0
    for _ in range(n_perm):
        rng.shuffle(perm)
        if pseudo_f(perm) >= obs - 1e-12:
            count += 1
    return obs, (count + 1) / (n_perm + 1)


# ----------------------------------------------------------------- data

ORDER = ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']
REF_MAP = {'Yes': 2, 'Partly': 1, 'No': 0}


def build_matrices(rows):
    """Reshapes the long table into question-by-system matrices."""
    questions = sorted({(r['domain'], r['question_id']) for r in rows})
    qi = {q: i for i, q in enumerate(questions)}
    mi = {m: j for j, m in enumerate(ORDER)}
    n, k = len(questions), len(ORDER)
    acc = np.zeros((n, k)); ref = np.zeros((n, k))
    exact = np.zeros((n, k)); safe = np.zeros((n, k)); evid = np.zeros((n, k))
    for r in rows:
        i, j = qi[(r['domain'], r['question_id'])], mi[r['model']]
        acc[i, j] = r['accuracy'] == 'Correct'
        ref[i, j] = REF_MAP[r['glr']]
        exact[i, j] = r['glr'] == 'Yes'
        safe[i, j] = r['safety'] in ('Minor', 'Major')
        evid[i, j] = r['evidence'] == 'Yes'
    domains = [q[0] for q in questions]
    return acc, ref, exact, safe, evid, domains, questions


# ----------------------------------------------------------------- report

def cmp_line(label, reported, got, tol=0.002):
    ok = 'OK' if (reported is None or abs(got - reported) <= tol) else '>>> DEVIATION'
    rep = '-' if reported is None else f'{reported:g}'
    print(f'  {label:<48s} reported {rep:>10s}   computed {got:>10.4f}   {ok}')


def main():
    rows = list(csv.DictReader(open(ANSWERS, encoding='utf-8')))
    acc, ref, exact, safe, evid, domains, questions = build_matrices(rows)
    PAIRS = [(0, 1), (0, 2), (1, 2)]
    PNAME = ['Open Evidence vs GPT-5.5', 'Open Evidence vs Sonar', 'GPT-5.5 vs Sonar']

    print('=' * 100)
    print('1  TABLE 3: DESCRIPTIVES PER SYSTEM  (n = 60 responses each)')
    print('=' * 100)
    for j, m in enumerate(ORDER):
        a, e, s, v = int(acc[:, j].sum()), int(exact[:, j].sum()), int(safe[:, j].sum()), int(evid[:, j].sum())
        ref_counts = collections.Counter(ref[:, j])
        print(f'  {m}')
        print(f'     accuracy correct        {a:2d}/60 = {100*a/60:5.1f} %   Wilson CI {wilson_ci(a, 60)[0]:.1f}-{wilson_ci(a, 60)[1]:.1f}')
        print(f'     guideline reference yes {e:2d}/60 = {100*e/60:5.1f} %   Wilson CI {wilson_ci(e, 60)[0]:.1f}-{wilson_ci(e, 60)[1]:.1f}'
              f'   partly {int(ref_counts[1]):2d}   no {int(ref_counts[0]):2d}   mean ordinal {ref[:, j].mean():.2f}')
        print(f'     safety concern (minor)  {s:2d}/60 = {100*s/60:5.1f} %')
        print(f'     evidence quality yes    {v:2d}/60 = {100*v/60:5.1f} %   Wilson CI {wilson_ci(v, 60)[0]:.1f}-{wilson_ci(v, 60)[1]:.1f}')
    s_all = int(safe.sum())
    print(f'  safety concern, all 180 responses: {s_all} = {100*s_all/180:.1f} %, Wilson CI '
          f'{wilson_ci(s_all, 180)[0]:.1f}-{wilson_ci(s_all, 180)[1]:.1f}')

    print()
    print('=' * 100)
    print('2  OMNIBUS TESTS  (Table 3, column P value)')
    print('=' * 100)
    for label, mat, rq, rp in [('Accuracy, Cochran Q', acc, 6.125, 0.0468),
                               ('Exact guideline reference, Cochran Q', exact, 13.333, 0.0013),
                               ('Safety concern, Cochran Q', safe, 2.800, 0.247),
                               ('Evidence quality, Cochran Q', evid, 17.375, 0.0002)]:
        q = cochran_q(mat)
        cmp_line(f'{label} - statistic', rq, q)
        cmp_line(f'{label} - p', rp, chi2_sf_df2(q))
    f = friedman(ref)
    cmp_line('Guideline reference three-level, Friedman - statistic', 14.230, f)
    cmp_line('Guideline reference three-level, Friedman - p', 0.000813, chi2_sf_df2(f))

    print()
    print('=' * 100)
    print('3  PAIRWISE CONTRASTS, EXACT McNEMAR WITH HOLM CORRECTION')
    print('   (guideline reference is tested at topic level instead: 01_topic_level_contrasts.py)')
    print('=' * 100)
    for label, mat, raw_rep, holm_rep in [
            ('Accuracy', acc, [1.000, 0.065, 0.092], [1.000, 0.196, 0.196]),
            ('Safety concern', safe, [0.625, 0.375, 1.000], [1.000, 1.000, 1.000]),
            ('Evidence quality', evid, [0.375, 0.0010, 0.0063], [0.375, 0.0029, 0.0127])]:
        print(f'  -- {label}')
        ps = []
        for (a_, b_), nm in zip(PAIRS, PNAME):
            n10, n01, p = mcnemar_exact(mat[:, a_], mat[:, b_])
            ps.append(p)
            diff = 100 * (mat[:, a_].mean() - mat[:, b_].mean())
            print(f'     {nm:<28s} difference {diff:+6.1f} pp   discordant b={n10:2d} c={n01:2d}')
        for nm, p, r in zip(PNAME, ps, raw_rep):
            cmp_line(f'   {nm} - raw p', r, p)
        for nm, p, r in zip(PNAME, holm(ps), holm_rep):
            cmp_line(f'   {nm} - Holm p', r, p)

    print()
    print('=' * 100)
    print('4  INTER-RATER AGREEMENT OF THE INDEPENDENT RATINGS  (ratings_raters.csv)')
    print('=' * 100)
    raters = list(csv.DictReader(open(RATERS, encoding='utf-8')))
    # AC1 divides chance agreement by the number of categories minus one; the
    # manuscript uses the categories actually assigned by either rater (two for
    # safety concern, three otherwise). With the full scale AC1 would rise by up to 0.02.
    for col, rep_ag, rep_k, rep_ac in [
            ('accuracy', 92.2, 0.707, 0.910),
            ('guideline_reference', 88.9, 0.814, 0.842),
            ('safety_concern', 95.0, 0.289, 0.946),
            ('evidence_level', 88.3, 0.501, 0.868)]:
        x = [r['rater_1_' + col] for r in raters]
        y = [r['rater_2_' + col] for r in raters]
        cats = sorted(set(x) | set(y))
        ag = 100 * sum(1 for i in range(len(x)) if x[i] == y[i]) / len(x)
        cmp_line(f'{col} - exact agreement %', rep_ag, ag, tol=0.15)
        cmp_line(f'{col} - Cohen kappa', rep_k, cohen_kappa(x, y, cats), tol=0.02)
        cmp_line(f'{col} - Gwet AC1', rep_ac, gwet_ac1(x, y, cats), tol=0.02)
    print('  Evidence quality: ratings of the second round, after the construct had been clarified')
    print('  (quality of the cited sources, not the grade of the recommendation); 21 adjudicated cases.')

    print()
    print('=' * 100)
    print('5  MARGINAL DOMAIN EFFECT, PERMUTATION TEST AT QUESTION LEVEL')
    print('=' * 100)
    DOM = ['Domain 1', 'Domain 2', 'Domain 3']
    domain_ps = []
    for label, mat, rep_f, rep_p in [
            ('Exact guideline reference', exact, 5.005, 0.011),
            ('Guideline reference three-level', ref, 2.902, 0.069),
            ('Accuracy', acc, 0.565, 0.60)]:
        per_q = mat.mean(axis=1)
        F, p = permutation_domain_effect(per_q, domains, n_perm=20000)
        domain_ps.append(p)
        means = [per_q[[i for i, d in enumerate(domains) if d == g]].mean() for g in DOM]
        print(f'  {label}')
        print(f'     domain means  D1 {means[0]:.3f}   D2 {means[1]:.3f}   D3 {means[2]:.3f}')
        cmp_line('     pseudo-F', rep_f, F, tol=0.35)
        cmp_line('     permutation p', rep_p, p, tol=0.02)
    print('  Holm over the two guideline reference scales: %s'
          % '  '.join('%.4f' % v for v in holm(domain_ps[:2])))
    # pairwise domain contrasts on exact reference, permutation pseudo-F over two domains
    per_q = exact.mean(axis=1)
    ps, names = [], []
    for a_, b_ in [('Domain 1', 'Domain 2'), ('Domain 1', 'Domain 3'), ('Domain 2', 'Domain 3')]:
        idx = [i for i, d in enumerate(domains) if d in (a_, b_)]
        F, p = permutation_domain_effect(per_q[idx], [domains[i] for i in idx], n_perm=20000)
        ps.append(p); names.append('%s vs %s' % (a_, b_))
        da = per_q[[i for i, d in enumerate(domains) if d == a_]].mean()
        db = per_q[[i for i, d in enumerate(domains) if d == b_]].mean()
        print(f'     {a_} vs {b_}: difference {100*(da-db):+.1f} pp, pseudo-F {F:.3f}, p {p:.4f}')
    print('     Holm over the three domain pairs: %s' % '  '.join('%s %.4f' % (n, h) for n, h in zip(names, holm(ps))))
    print('  20,000 permutations here; p values vary in the third decimal between seeds.')
    print(REFERENCE)


REFERENCE = """
Reference values - a run must reproduce these (Table 3 and Results 3.1-3.7):
  Accuracy correct          54 / 54 / 47   Cochran Q p 0.047, no pairwise contrast after Holm
  Exact reference           21 / 41 / 31   Cochran Q p 0.001; Friedman p < 0.001
  Guideline reference no    11 /  0 / 14   mean ordinal 1.17 / 1.68 / 1.28
  Safety concern             4 /  2 /  1   Cochran Q p 0.247; 7 of 180 = 3.9 % (1.9-7.8)
  Evidence quality yes      59 / 56 / 46   Cochran Q p 0.0002; Holm McNemar 0.375 / 0.003 / 0.013
  Agreement                 92.2 / 88.9 / 95.0 / 88.3 % (kappa 0.707 / 0.814 / 0.289 / 0.501; AC1 0.910 / 0.842 / 0.946 / 0.868)
  Domain effect             exact reference pseudo-F 5.005, p 0.011 (Holm 0.021); accuracy 0.565, p 0.60
                            domain 2 vs 3: +26.7 pp, Holm p 0.028
"""

if __name__ == '__main__':
    main()
