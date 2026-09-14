# -*- coding: utf-8 -*-
"""02 - Cliff's delta for the three-level guideline reference, bootstrap over topics.

Produces for the manuscript:
  Table 4, column "Cliff's delta (95% CI)":
    GPT-5.5 vs Open Evidence           delta +0.39  (CI 0.14 to 0.60)
    GPT-5.5 vs Sonar Reasoning Pro     delta +0.24  (CI 0.11 to 0.37)
    Sonar Reasoning Pro vs Open Evidence delta +0.10 (CI -0.10 to 0.29)

Point estimate at response level; the intervals are drawn over the 30 topics,
because the two questions of a topic are not independent. Bias-corrected and
accelerated bootstrap (BCa), 5,000 resamples, fixed seed. The response-level
interval is printed alongside for comparison but is not reported.

Input: ../data/answers_v2.csv
Standard library only.
"""
import csv, os, collections, itertools, random, math

HERE = os.path.dirname(os.path.abspath(__file__))
ANSWERS = os.path.join(HERE, '..', 'data', 'answers_v2.csv')

SEED, NBOOT = 20260820, 5000
ORD = {'No':0,'Partly':1,'Yes':2}
MODELS = ['Open Evidence','GPT-5.5','Sonar Reasoning Pro']

rows = list(csv.DictReader(open(ANSWERS, encoding='utf-8')))
by = collections.defaultdict(dict)
for r in rows:
    t = (r['domain'], r['question_id'][:-1])
    by[t].setdefault(r['model'], []).append(ORD[r['glr']])
topics = sorted(by, key=lambda x: (x[0], int(x[1])))

def cliff(x, y):
    gt = sum(1 for a in x for b in y if a > b)
    lt = sum(1 for a in x for b in y if a < b)
    return (gt - lt) / (len(x) * len(y))

def flat(sel, m):
    return [v for t in sel for v in by[t][m]]

def bca(boot, obs, jack):
    boot = sorted(boot); n = len(boot)
    z0 = sum(1 for b in boot if b < obs) / n
    if z0 <= 0: z0 = 1/(2*n)
    if z0 >= 1: z0 = 1 - 1/(2*n)
    # inverse of the standard normal distribution
    def qn(p):
        a=[-3.969683028665376e+01,2.209460984245205e+02,-2.759285104469687e+02,
            1.383577518672690e+02,-3.066479806614716e+01,2.506628277459239e+00]
        b=[-5.447609879822406e+01,1.615858368580409e+02,-1.556989798598866e+02,
            6.680131188771972e+01,-1.328068155288572e+01]
        c=[-7.784894002430293e-03,-3.223964580411365e-01,-2.400758277161838e+00,
           -2.549732539343734e+00,4.374664141464968e+00,2.938163982698783e+00]
        d=[7.784695709041462e-03,3.224671290700398e-01,2.445134137142996e+00,3.754408661907416e+00]
        pl=0.02425
        if p<pl:
            q=math.sqrt(-2*math.log(p))
            return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
        if p>1-pl:
            q=math.sqrt(-2*math.log(1-p))
            return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
        q=p-0.5; r=q*q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q/(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    def cdf(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
    z0h = qn(z0)
    jm = sum(jack)/len(jack)
    num = sum((jm-j)**3 for j in jack); den = 6*(sum((jm-j)**2 for j in jack))**1.5
    a = num/den if den else 0.0
    out=[]
    for alpha in (0.025, 0.975):
        za = qn(alpha)
        p = cdf(z0h + (z0h+za)/(1-a*(z0h+za)))
        out.append(boot[min(n-1, max(0, int(round(p*(n-1)))))])
    return out

print("Cliff's delta, three-level guideline reference")
print("%-40s %8s %22s %22s"%("Contrast","delta","CI response level (60)","CI topic level (30)"))
rnd = random.Random(SEED)
for a,b in itertools.combinations(MODELS,2):
    obs = cliff(flat(topics,b), flat(topics,a))   # b versus a
    # Bootstrap at response level: resample questions
    qs = [(t,i) for t in topics for i in (0,1)]
    boot_i=[]
    for _ in range(NBOOT):
        s=[qs[rnd.randrange(len(qs))] for _ in qs]
        x=[by[t][b][i] for t,i in s]; y=[by[t][a][i] for t,i in s]
        boot_i.append(cliff(x,y))
    jack_i=[]
    for k in range(len(qs)):
        s=qs[:k]+qs[k+1:]
        jack_i.append(cliff([by[t][b][i] for t,i in s],[by[t][a][i] for t,i in s]))
    ci_i = bca(boot_i, obs, jack_i)
    # Bootstrap at topic level: resample whole topics
    boot_t=[]
    for _ in range(NBOOT):
        s=[topics[rnd.randrange(len(topics))] for _ in topics]
        boot_t.append(cliff(flat(s,b), flat(s,a)))
    jack_t=[]
    for k in range(len(topics)):
        s=topics[:k]+topics[k+1:]
        jack_t.append(cliff(flat(s,b), flat(s,a)))
    ci_t = bca(boot_t, obs, jack_t)
    print("%-40s %+8.3f   %8.3f to %6.3f   %8.3f to %6.3f"
          %("%s vs %s"%(b,a), obs, ci_i[0],ci_i[1], ci_t[0],ci_t[1]))

REFERENCE = """
Reference values - a run must reproduce these (topic-level CI is the reported one):
  GPT-5.5 vs Open Evidence              +0.391   CI  0.138 to 0.597
  Sonar Reasoning Pro vs Open Evidence  +0.104   CI -0.101 to 0.293
  Sonar Reasoning Pro vs GPT-5.5        -0.241   CI -0.373 to -0.107  (reported as GPT-5.5 vs Sonar +0.24, 0.11 to 0.37)
"""
print(REFERENCE)
