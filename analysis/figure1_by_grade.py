#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Figure 1 - Guideline reference by grade of recommendation.

Produces for the manuscript:
  Figure 1 (slope chart), Results 3.6 and the numbers quoted there:
    Open Evidence         evidence-graded 0.71  vs  good practice points 1.47   Holm p = 0.0045
    GPT-5.5               evidence-graded 1.88  vs  good practice points 1.56   Holm p = 0.21
    Sonar Reasoning Pro   evidence-graded 1.25  vs  good practice points 1.31   Holm p = 0.61
  Exact reference counts: Open Evidence 1 of 24 evidence-graded responses and
  20 of 36 good practice point responses; GPT-5.5 21 of 24 and 20 of 36.

Design
  The 60 questions form 30 topics; both questions of a topic derive from the same
  source recommendation and therefore share its grade. The unit of analysis is the
  topic mean of the ordinal guideline reference score (no = 0, partly = 1, yes = 2).
  Twelve topics rest on graded evidence (SIGN A, B or 0), eighteen on a good
  practice point (GPP). Error bars are the standard error of the mean over topics.

  The p value per system is a permutation test of the difference between the two
  grade groups, permuting grade labels within clinical domain so that the domain
  effect is not measured along with it. 50,000 permutations, fixed seed, Holm
  correction over the three systems. This is the same test as in
  reproduce_statistics.py, section 4; it is repeated here so that the figure
  script is self-contained.

Input
  ../data/answers_v2.csv      180 rows: domain, question_id, model, glr, ...
  ../data/items_master.csv     60 rows: question_id, sign_grade, ...

Output
  ../figures/figure1_guideline_reference_by_grade.pdf and .png
  Reference values printed to stdout.

Requires matplotlib. Everything else is standard library.
"""
import csv, os, math, random, collections, itertools

HERE = os.path.dirname(os.path.abspath(__file__))
ANSWERS = os.path.join(HERE, '..', 'data', 'answers_v2.csv')
ITEMS = os.path.join(HERE, '..', 'data', 'items_master.csv')
OUTDIR = os.path.join(HERE, '..', 'figures')
OUTNAME = 'figure1_guideline_reference_by_grade'

SEED, NPERM = 20260812, 50000
ORD = {'No': 0, 'Partly': 1, 'Yes': 2}
MODELS = ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']
DOMAINS = ['Domain 1', 'Domain 2', 'Domain 3']


def topic_of(domain, question_id):
    """'Domain 1', '10a' -> ('Domain 1', '10'). Question IDs end in a or b."""
    return (domain, question_id[:-1])


def load():
    answers = list(csv.DictReader(open(ANSWERS, encoding='utf-8')))
    items = list(csv.DictReader(open(ITEMS, encoding='utf-8')))
    # items_master.question_id is 'Domain 1|10a'
    grade = {}
    for it in items:
        dom, qid = it['question_id'].split('|')
        t = topic_of(dom, qid)
        g = 'GPP' if it['sign_grade'] == 'GPP' else 'graded'
        if t in grade and grade[t] != g:
            raise ValueError('Inconsistent grade within topic %s' % (t,))
        grade[t] = g
    per_topic = collections.defaultdict(list)
    per_response = collections.defaultdict(list)
    for r in answers:
        t = topic_of(r['domain'], r['question_id'])
        per_topic[(r['model'], t)].append(ORD[r['glr']])
        per_response[(r['model'], grade[t])].append(r['glr'])
    topics = sorted(grade, key=lambda x: (x[0], int(x[1])))
    val = {k: sum(v) / len(v) for k, v in per_topic.items()}
    return topics, grade, val, per_response


def mean_sem(xs):
    n = len(xs)
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return m, sd / math.sqrt(n)


def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i])
    out, run = [0.] * len(ps), 0.
    for k, i in enumerate(o):
        run = max(run, ps[i] * (len(ps) - k))
        out[i] = min(1., run)
    return out


def grade_permutation_p(model, topics, grade, val):
    """Difference graded minus GPP, summed over domains, labels permuted within domain."""
    labels = [grade[t] for t in topics]

    def stat(lab):
        L = dict(zip(topics, lab))
        s = 0.0
        for d in DOMAINS:
            idx = [t for t in topics if t[0] == d]
            A = [val[(model, t)] for t in idx if L[t] == 'graded']
            B = [val[(model, t)] for t in idx if L[t] == 'GPP']
            if A and B:
                s += sum(A) / len(A) - sum(B) / len(B)
        return abs(s)

    obs = stat(labels)
    rnd, hits = random.Random(SEED), 0
    for _ in range(NPERM):
        lab = list(labels)
        for d in DOMAINS:
            idx = [i for i, t in enumerate(topics) if t[0] == d]
            sub = [lab[i] for i in idx]
            rnd.shuffle(sub)
            for i, v in zip(idx, sub):
                lab[i] = v
        if stat(lab) >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (NPERM + 1)


def draw(summary, n_graded, n_gpp):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    style = {'Open Evidence': dict(color='#0072B2', marker='o', ls='-', lw=3.0, ms=11),
             'GPT-5.5': dict(color='#999999', marker='^', ls='--', lw=1.8, ms=10),
             'Sonar Reasoning Pro': dict(color='#666666', marker='s', ls=':', lw=1.8, ms=10)}
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    x = [0, 1]
    for m in ['GPT-5.5', 'Sonar Reasoning Pro', 'Open Evidence']:
        (mg, sg), (mp, sp) = summary[m]['graded'], summary[m]['GPP']
        ax.errorbar(x, [mg, mp], yerr=[sg, sp], capsize=4, elinewidth=1.2,
                    ecolor=style[m]['color'], label=m, **style[m])
    ax.set_xlim(-0.35, 1.35)
    ax.set_ylim(0, 2)
    ax.set_yticks([0, 0.5, 1, 1.5, 2])
    ax.set_xticks(x)
    ax.set_xticklabels(['Evidence-graded\n(n = %d topics)' % n_graded,
                        'Good practice points\n(n = %d topics)' % n_gpp])
    ax.set_ylabel('Mean ordinal guideline reference\n(0 = no, 1 = partly, 2 = yes)')
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, loc='lower right')
    fig.tight_layout()
    os.makedirs(OUTDIR, exist_ok=True)
    for ext in ('pdf', 'png'):
        fig.savefig(os.path.join(OUTDIR, OUTNAME + '.' + ext), dpi=300)
    plt.close(fig)


def main():
    topics, grade, val, per_response = load()
    n_graded = sum(1 for t in topics if grade[t] == 'graded')
    n_gpp = len(topics) - n_graded

    summary, raw_p = {}, []
    print('Topic means of ordinal guideline reference, mean (SEM) over topics')
    print('%-22s %-16s %-16s %8s' % ('System', 'evidence-graded', 'GPP', 'p raw'))
    for m in MODELS:
        g = [val[(m, t)] for t in topics if grade[t] == 'graded']
        p = [val[(m, t)] for t in topics if grade[t] == 'GPP']
        summary[m] = {'graded': mean_sem(g), 'GPP': mean_sem(p)}
        raw_p.append(grade_permutation_p(m, topics, grade, val))
        print('%-22s %.2f (%.2f)      %.2f (%.2f)      %8.4f'
              % (m, *summary[m]['graded'], *summary[m]['GPP'], raw_p[-1]))
    adj = holm(raw_p)
    print('Holm-adjusted p over the three systems: %s'
          % '  '.join('%s %.4f' % (m, a) for m, a in zip(MODELS, adj)))

    print('\nExact reference (yes) by grade, responses')
    for m in MODELS:
        g, p = per_response[(m, 'graded')], per_response[(m, 'GPP')]
        print('%-22s evidence-graded %2d of %d    GPP %2d of %d'
              % (m, g.count('Yes'), len(g), p.count('Yes'), len(p)))

    draw(summary, n_graded, n_gpp)
    print('\nwritten: %s' % os.path.join(OUTDIR, OUTNAME + '.{pdf,png}'))
    print(REFERENCE)


REFERENCE = """
Reference values - a run must reproduce these:
  Topics                        12 evidence-graded, 18 good practice points
  Open Evidence                 0.71 (0.14)  vs  1.47 (0.13)   Holm p 0.0045
  GPT-5.5                       1.88 (0.07)  vs  1.56 (0.11)   Holm p 0.21
  Sonar Reasoning Pro           1.25 (0.17)  vs  1.31 (0.12)   Holm p 0.61
  Exact reference               Open Evidence  1 of 24 vs 20 of 36
                                GPT-5.5       21 of 24 vs 20 of 36
                                Sonar         13 of 24 vs 18 of 36
"""

if __name__ == '__main__':
    main()
