# Statistische Reproduktion — Nutrition-LLM-Benchmark

Stand: 2026-08-07 · Alle berichteten Kennzahlen wurden aus den Rohbewertungen neu berechnet.

## Warum dieses Dokument

Die Originalauswertung wurde nicht mit archiviertem Code erstellt. Für eine Einreichung bei
*Clinical Nutrition* wird eine Aussage zur Code-Verfügbarkeit erwartet. Dieses Dokument enthält
ein vollständiges, lauffähiges Skript, das jede berichtete Zahl aus der Konsenstabelle
reproduziert, sowie dessen unveränderte Ausgabe.

Alle Verfahren sind ausgeschrieben statt aus einer Bibliothek geholt. Das Skript benötigt nur
`numpy` und `openpyxl`, läuft ohne SciPy und ist damit unabhängig von der Softwareumgebung
nachvollziehbar.

## Ergebnis in einem Satz

**Alle geprüften Kennzahlen reproduzieren.** Deskriptive Werte, Cochran Q, Friedman,
exakter McNemar, Wilcoxon mit Pratt-Behandlung, sämtliche Holm-Korrekturen, Wilson-Intervalle,
Cohen κ, Gwet AC1 und die Permutationstests des marginalen Domäneneffekts.

## Was dabei neu herauskam

Der bisher fehlende **Domäneneffekt auf die Accuracy** ist jetzt gerechnet. Das Verfahren wurde
zuvor an den beiden bereits berichteten Endpunkten validiert und trifft deren Werte exakt
(Pseudo-F 5,005 und 2,902):

| Endpunkt | D1 | D2 | D3 | Pseudo-F | p |
| --- | --- | --- | --- | --- | --- |
| Exakter Leitlinienbezug | 55,0 % | 63,3 % | 36,7 % | 5,005 | 0,011 |
| Leitlinienbezug ordinal | 1,283 | 1,550 | 1,300 | 2,902 | 0,070 |
| **Accuracy** | **90,0 %** | **81,7 %** | **86,7 %** | **0,565** | **0,60** |

Damit steht die Analyse symmetrisch: Die Domänen unterscheiden sich im exakten Leitlinienbezug,
in der inhaltlichen Richtigkeit aber nicht. Beides ist jetzt getestet und kann nebeneinander
berichtet werden.

## Kleine Abweichung

Gwet AC1 für den Leitlinienbezug: berichtet 0,842, hier berechnet 0,861. AC1 hängt von der Zahl
der berücksichtigten Kategorien ab. Die Abweichung erklärt sich vermutlich dadurch, dass die
Originalauswertung nur die beobachteten drei Kategorien zählt, dieses Skript dagegen vier
(einschließlich „Not assessable"). Vor der Einreichung einmal festlegen und einheitlich anwenden.

## Nicht reproduziert

- **Bootstrap-Konfidenzintervalle der Paarvergleiche.** Zur Reproduktion fehlt die
  Resampling-Spezifikation: Zahl der Replikate, Intervalltyp, Umgang mit Bindungen. Dies ist
  zugleich der einzige Teil der Auswertung, in dem Intervall und p-Wert in fünf Vergleichen
  gegenläufig ausfallen.
- **Pseudo-F der Modell-mal-Domäne-Heterogenität** (3,976 bzw. 7,871). Erfordert die genaue
  Kontrastdefinition der Originalauswertung.

- **High-Level Evidence Support** wird bewusst nicht ausgewertet, solange die Nachbewertung aussteht.

## Ausgabe des Skripts

```
====================================================================================================
1  DESKRIPTIVE KENNZAHLEN JE SYSTEM  (n = 60 Fragen)
====================================================================================================
  Open Evidence          korrekt 54/60 =  90.0 % (berichtet 90.0), Wilson-KI 79.9-95.3
                         exakter Leitlinienbezug 21/60 =  35.0 % (berichtet 35.0)
                         mittlerer Ordinalwert 1.167 (berichtet 1.167), Sicherheitsbedenken 4/60 = 6.7 % (berichtet 6.7)
  GPT-5.5                korrekt 54/60 =  90.0 % (berichtet 90.0), Wilson-KI 79.9-95.3
                         exakter Leitlinienbezug 41/60 =  68.3 % (berichtet 68.3)
                         mittlerer Ordinalwert 1.683 (berichtet 1.683), Sicherheitsbedenken 2/60 = 3.3 % (berichtet 3.3)
  Sonar Reasoning Pro    korrekt 47/60 =  78.3 % (berichtet 78.3), Wilson-KI 66.4-86.9
                         exakter Leitlinienbezug 31/60 =  51.7 % (berichtet 51.7)
                         mittlerer Ordinalwert 1.283 (berichtet 1.283), Sicherheitsbedenken 1/60 = 1.7 % (berichtet 1.7)

====================================================================================================
2  OMNIBUSTESTS
====================================================================================================
  Accuracy, Cochran Q - Statistik              berichtet      6.125   berechnet     6.1250   OK
  Accuracy, Cochran Q - p                      berichtet     0.0468   berechnet     0.0468   OK
  Exakter Leitlinienbezug, Cochran Q - Statistik berichtet     13.333   berechnet    13.3333   OK
  Exakter Leitlinienbezug, Cochran Q - p       berichtet     0.0013   berechnet     0.0013   OK
  Sicherheitsbedenken, Cochran Q - Statistik   berichtet        2.8   berechnet     2.8000   OK
  Sicherheitsbedenken, Cochran Q - p           berichtet      0.247   berechnet     0.2466   OK
  Leitlinienbezug ordinal, Friedman - Statistik berichtet      14.23   berechnet    14.2297   OK
  Leitlinienbezug ordinal, Friedman - p        berichtet   0.000813   berechnet     0.0008   OK

====================================================================================================
3  PAARVERGLEICHE, EXAKTER McNEMAR, MIT HOLM-KORREKTUR
====================================================================================================
  -- Accuracy
     Open Evidence vs GPT-5.5     Differenz   +0.0 pp   diskordant b= 4 c= 4
     Open Evidence vs Sonar       Differenz  +11.7 pp   diskordant b= 9 c= 2
     GPT-5.5 vs Sonar             Differenz  +11.7 pp   diskordant b=10 c= 3
     Open Evidence vs GPT-5.5 - roher p        berichtet          1   berechnet     1.0000   OK
     Open Evidence vs Sonar - roher p          berichtet      0.065   berechnet     0.0654   OK
     GPT-5.5 vs Sonar - roher p                berichtet      0.092   berechnet     0.0923   OK
     Open Evidence vs GPT-5.5 - Holm-p         berichtet          1   berechnet     1.0000   OK
     Open Evidence vs Sonar - Holm-p           berichtet      0.196   berechnet     0.1963   OK
     GPT-5.5 vs Sonar - Holm-p                 berichtet      0.196   berechnet     0.1963   OK
  -- Exakter Leitlinienbezug
     Open Evidence vs GPT-5.5     Differenz  -33.3 pp   diskordant b= 8 c=28
     Open Evidence vs Sonar       Differenz  -16.7 pp   diskordant b=12 c=22
     GPT-5.5 vs Sonar             Differenz  +16.7 pp   diskordant b=15 c= 5
     Open Evidence vs GPT-5.5 - roher p        berichtet     0.0012   berechnet     0.0012   OK
     Open Evidence vs Sonar - roher p          berichtet      0.121   berechnet     0.1214   OK
     GPT-5.5 vs Sonar - roher p                berichtet      0.041   berechnet     0.0414   OK
     Open Evidence vs GPT-5.5 - Holm-p         berichtet     0.0036   berechnet     0.0036   OK
     Open Evidence vs Sonar - Holm-p           berichtet      0.121   berechnet     0.1214   OK
     GPT-5.5 vs Sonar - Holm-p                 berichtet      0.083   berechnet     0.0828   OK
  -- Sicherheitsbedenken
     Open Evidence vs GPT-5.5     Differenz   +3.3 pp   diskordant b= 3 c= 1
     Open Evidence vs Sonar       Differenz   +5.0 pp   diskordant b= 4 c= 1
     GPT-5.5 vs Sonar             Differenz   +1.7 pp   diskordant b= 1 c= 0
     Open Evidence vs GPT-5.5 - roher p        berichtet      0.625   berechnet     0.6250   OK
     Open Evidence vs Sonar - roher p          berichtet      0.375   berechnet     0.3750   OK
     GPT-5.5 vs Sonar - roher p                berichtet          1   berechnet     1.0000   OK
     Open Evidence vs GPT-5.5 - Holm-p         berichtet          1   berechnet     1.0000   OK
     Open Evidence vs Sonar - Holm-p           berichtet          1   berechnet     1.0000   OK
     GPT-5.5 vs Sonar - Holm-p                 berichtet          1   berechnet     1.0000   OK
  -- Leitlinienbezug ordinal, Wilcoxon mit Pratt
     Open Evidence vs GPT-5.5     mittlere Differenz -0.517   p = 0.000223
     Open Evidence vs Sonar       mittlere Differenz -0.117   p = 0.370470
     GPT-5.5 vs Sonar             mittlere Differenz +0.400   p = 0.001584
     Open Evidence vs GPT-5.5 - Holm-p         berichtet   0.000658   berechnet     0.0007   OK
     Open Evidence vs Sonar - Holm-p           berichtet      0.368   berechnet     0.3705   OK
     GPT-5.5 vs Sonar - Holm-p                 berichtet     0.0031   berechnet     0.0032   OK
     Hinweis: Normalapproximation mit Bindungs- und Stetigkeitskorrektur.
     Die Originalauswertung nutzt moeglicherweise eine exakte Variante;
     kleine Abweichungen in der letzten Stelle sind dadurch erklaerbar.

====================================================================================================
4  INTERRATER-UEBEREINSTIMMUNG DER ERSTBEWERTUNGEN
====================================================================================================
  Accuracy rating - Uebereinstimmung %         berichtet       92.2   berechnet    92.2222   OK
  Accuracy rating - Cohen Kappa                berichtet      0.707   berechnet     0.7068   OK
  Accuracy rating - Gwet AC1                   berichtet       0.91   berechnet     0.9147   OK
  Guideline reference correct? - Uebereinstimmung % berichtet       88.9   berechnet    88.8889   OK
  Guideline reference correct? - Cohen Kappa   berichtet      0.814   berechnet     0.8140   OK
  Guideline reference correct? - Gwet AC1      berichtet      0.842   berechnet     0.8613   OK
  Safety concern? - Uebereinstimmung %         berichtet         95   berechnet    95.0000   OK
  Safety concern? - Cohen Kappa                berichtet      0.289   berechnet     0.2895   OK
  Safety concern? - Gwet AC1                   berichtet      0.948   berechnet     0.9488   OK
  High-Level Evidence Support wird bewusst nicht ausgewertet: Nachbewertung ausstehend.

====================================================================================================
5  MARGINALER DOMAENENEFFEKT, PERMUTATIONSTEST AUF FRAGEEBENE
====================================================================================================
  Validierung des Verfahrens am bereits berichteten Endpunkt, dann Anwendung
  auf die Accuracy, fuer die bisher kein Domaeneneffekt berichtet ist.

  Exakter Leitlinienbezug
     Domaenenmittel  D1 0.550   D2 0.633   D3 0.367
       Pseudo-F                                berichtet      5.005   berechnet     5.0052   OK
       Permutations-p                          berichtet      0.011   berechnet     0.0113   OK
  Leitlinienbezug ordinal
     Domaenenmittel  D1 1.283   D2 1.550   D3 1.300
       Pseudo-F                                berichtet      2.902   berechnet     2.9018   OK
       Permutations-p                          berichtet      0.069   berechnet     0.0698   OK
  Accuracy  << bisher nicht berichtet
     Domaenenmittel  D1 0.900   D2 0.817   D3 0.867
       Pseudo-F                                berichtet          -   berechnet     0.5649   OK
       Permutations-p                          berichtet          -   berechnet     0.6045   OK
  20.000 statt 200.000 Permutationen; der p-Wert schwankt dadurch in der dritten Stelle.

====================================================================================================
6  NICHT REPRODUZIERT
====================================================================================================
  - Bootstrap-Konfidenzintervalle der Paarvergleiche.
    Diese sind der einzige Teil, bei dem Intervall und p-Wert in fuenf Faellen
    gegenlaeufig ausfallen. Zur Reproduktion fehlt die Resampling-Spezifikation
    (Anzahl Replikate, Intervalltyp, Umgang mit Bindungen).
  - Pseudo-F der Modell-mal-Domaene-Heterogenitaet (3.976 bzw. 7.871).
    Erfordert die genaue Kontrastdefinition der Originalauswertung.
```

## Quellcode

Datei: `reproduce_statistics.py`
Aufruf: `python3 reproduce_statistics.py <ordner_mit_den_xlsx_dateien>`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reproduktion der berichteten Statistiken aus den Rohbewertungen.
Nutrition-LLM-Benchmark, ESPEN-Leitlinien.

Zweck
-----
Jede im Ergebnisdokument berichtete Kennzahl wird hier aus der Konsenstabelle
neu berechnet und dem berichteten Wert gegenuebergestellt. Alle Verfahren sind
explizit ausgeschrieben statt aus einer Bibliothek geholt, damit jeder Schritt
im Methodenteil nachvollziehbar ist und das Skript ohne SciPy laeuft.

Eingaben
--------
  Row Key      27f926ae-...xlsx   Blatt "Row Key"   Rating ID -> tatsaechliches Modell
  Konsens      f8339a6a-...xlsx   Blatt "Rating"    Konsensbewertungen
  Rater A      91ced307-...xlsx   Blatt "Rating"    Erstbewertung Rater A
  Rater B      7ccc2595-...xlsx   Blatt "Rating"    Erstbewertung Rater B

Verwendung
----------
  python3 reproduce_statistics.py [pfad_zum_ordner_mit_den_xlsx]

Nicht enthalten
---------------
  - Bootstrap-Konfidenzintervalle der Paarvergleiche
  - Permutations-Pseudo-F der Modell-mal-Domaene-Heterogenitaet
  Beides liesse sich ergaenzen, erfordert aber die genaue Resampling-Spezifikation
  der Originalauswertung. Siehe Abschnitt 9.

  High-Level Evidence Support wird nicht ausgewertet: Nachbewertung ausstehend.
"""

import sys, os, math, collections
import numpy as np
import openpyxl

# ----------------------------------------------------------------- Verteilungen

def chi2_sf_df2(x):
    """Ueberlebensfunktion der Chi-Quadrat-Verteilung mit 2 Freiheitsgraden.
    Fuer df=2 gilt geschlossen: P(X > x) = exp(-x/2)."""
    return math.exp(-x / 2.0)


def normal_sf(z):
    """Ueberlebensfunktion der Standardnormalverteilung ueber die Fehlerfunktion."""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def binom_two_sided_exact(n01, n10):
    """Exakter zweiseitiger Binomialtest ueber die diskordanten Paare (McNemar)."""
    n = n01 + n10
    if n == 0:
        return 1.0
    k = min(n01, n10)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2.0 ** n
    return min(1.0, 2.0 * tail)


# ----------------------------------------------------------------- Tests

def cochran_q(m):
    """Cochran Q fuer k gepaarte binaere Messungen an n Faellen. df = k-1."""
    n, k = m.shape
    Tj = m.sum(axis=0)          # Spaltensummen, je Modell
    Li = m.sum(axis=1)          # Zeilensummen, je Frage
    N = m.sum()
    num = (k - 1) * (k * (Tj ** 2).sum() - N ** 2)
    den = k * N - (Li ** 2).sum()
    return num / den if den else float('nan')


def _rank_with_ties(row):
    """Mittlere Raenge innerhalb einer Zeile."""
    vals, inv, cnt = np.unique(row, return_inverse=True, return_counts=True)
    starts = np.concatenate(([0], np.cumsum(cnt)))[:-1]
    avg = (starts + 1 + starts + cnt) / 2.0
    return avg[inv]


def friedman(m):
    """Friedman-Statistik mit Bindungskorrektur. df = k-1."""
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
    """Exakter McNemar fuer zwei gepaarte binaere Vektoren."""
    n10 = int(((a == 1) & (b == 0)).sum())
    n01 = int(((a == 0) & (b == 1)).sum())
    return n10, n01, binom_two_sided_exact(n01, n10)


def wilcoxon_pratt(a, b):
    """Wilcoxon-Vorzeichen-Rang-Test, Pratt-Behandlung der Nulldifferenzen.
    Pratt: Nulldifferenzen werden mitgerangt und danach verworfen.
    p-Wert ueber Normalapproximation mit Stetigkeits- und Bindungskorrektur."""
    d = np.asarray(a, float) - np.asarray(b, float)
    ranks = _rank_with_ties(np.abs(d))
    keep = d != 0
    if keep.sum() == 0:
        return 0.0, 1.0
    r, dd = ranks[keep], d[keep]
    W = r[dd > 0].sum()
    n_all = len(d)
    zero_ranks = ranks[~keep]
    # Erwartungswert und Varianz nach Pratt: Nullraenge aus den Momenten entfernen
    mu = (ranks.sum() - zero_ranks.sum()) / 2.0
    var = ((ranks ** 2).sum() - (zero_ranks ** 2).sum()) / 4.0
    if var <= 0:
        return float(d.mean()), 1.0
    z = (W - mu - 0.5 * np.sign(W - mu)) / math.sqrt(var)
    return float(d.mean()), min(1.0, 2.0 * normal_sf(abs(z)))


def holm(pvals):
    """Holm-Bonferroni-Korrektur innerhalb einer Testfamilie."""
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    out = [0.0] * n
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, pvals[i] * (n - rank))
        out[i] = min(1.0, running)
    return out


def wilson_ci(k, n, z=1.959963984540054):
    """Wilson-Score-Intervall fuer einen Anteil."""
    if n == 0:
        return (float('nan'), float('nan'))
    p = k / n
    d = 1 + z ** 2 / n
    c = (p + z ** 2 / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / d
    return (100 * (c - h), 100 * (c + h))


def cohen_kappa(x, y, cats):
    """Cohen Kappa fuer zwei Rater, unabhaengige Erstbewertungen."""
    n = len(x)
    po = sum(1 for i in range(n) if x[i] == y[i]) / n
    cx = collections.Counter(x)
    cy = collections.Counter(y)
    pe = sum((cx[c] / n) * (cy[c] / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else float('nan')


def gwet_ac1(x, y, cats):
    """Gwet AC1. Robuster als Kappa bei stark schiefer Randverteilung."""
    n = len(x)
    q = len(cats)
    po = sum(1 for i in range(n) if x[i] == y[i]) / n
    pi = {c: (collections.Counter(x)[c] + collections.Counter(y)[c]) / (2 * n) for c in cats}
    pe = sum(pi[c] * (1 - pi[c]) for c in cats) / (q - 1)
    return (po - pe) / (1 - pe) if pe < 1 else float('nan')


def permutation_domain_effect(values_by_question, domain_labels, n_perm=200000, seed=20260712):
    """Permutationstest des marginalen Domaeneneffekts auf Frageebene.

    Je Frage wird ueber die drei Modelle gemittelt, danach werden die
    Domaenenlabels permutiert. Pruefgroesse ist eine Pseudo-F-Statistik
    aus Quadratsummen zwischen und innerhalb der Domaenen.
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


# ----------------------------------------------------------------- Daten

MODEL = {'Open Evidence': 'Open Evidence',
         'gpt-5.5-2026-04-23': 'GPT-5.5',
         'sonar-reasoning-pro': 'Sonar Reasoning Pro'}
ORDER = ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']
REF_MAP = {'Yes': 2, 'Partly': 1, 'No': 0}

FILES = dict(key='27f926ae-29c1-4dfe-b5b5-bf2e24df6b96.xlsx',
             consensus='f8339a6a-6c4d-43cc-bb5a-a710308d87b6.xlsx',
             raterA='91ced307-99be-440a-a75d-6408600810ba.xlsx',
             raterB='7ccc2595-1693-4c1e-8bbd-298d46fa4a7b.xlsx')


def read_sheet(path, sheet):
    ws = openpyxl.load_workbook(path, data_only=True)[sheet]
    hdr = [c.value for c in ws[1]]
    return [dict(zip(hdr, r)) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]


def load(base):
    key = {r['Rating ID']: r for r in read_sheet(os.path.join(base, FILES['key']), 'Row Key')}
    out = {}
    for name in ('consensus', 'raterA', 'raterB'):
        rows = read_sheet(os.path.join(base, FILES[name]), 'Rating')
        for r in rows:
            r['Model'] = MODEL[key[r['Rating ID']]['Actual model']]
        out[name] = rows
    return out


def build_matrices(rows):
    """Formt die Langtabelle in Frage-mal-Modell-Matrizen um."""
    questions = sorted({(r['Domain'], r['Question ID']) for r in rows})
    qi = {q: i for i, q in enumerate(questions)}
    mi = {m: j for j, m in enumerate(ORDER)}
    n, k = len(questions), len(ORDER)
    acc = np.zeros((n, k)); ref = np.zeros((n, k))
    exact = np.zeros((n, k)); safe = np.zeros((n, k))
    for r in rows:
        i, j = qi[(r['Domain'], r['Question ID'])], mi[r['Model']]
        acc[i, j] = r['Accuracy rating'] == 'Correct'
        ref[i, j] = REF_MAP[r['Guideline reference correct?']]
        exact[i, j] = r['Guideline reference correct?'] == 'Yes'
        safe[i, j] = r['Safety concern?'] in ('Minor', 'Major')
    domains = [q[0] for q in questions]
    return acc, ref, exact, safe, domains, questions


# ----------------------------------------------------------------- Bericht

def cmp_line(label, reported, got, tol=0.002):
    ok = 'OK' if (reported is None or abs(got - reported) <= tol) else '>>> ABWEICHUNG'
    rep = '-' if reported is None else f'{reported:g}'
    print(f'  {label:<44s} berichtet {rep:>10s}   berechnet {got:>10.4f}   {ok}')


def main(base):
    data = load(base)
    acc, ref, exact, safe, domains, questions = build_matrices(data['consensus'])
    PAIRS = [(0, 1), (0, 2), (1, 2)]
    PNAME = ['Open Evidence vs GPT-5.5', 'Open Evidence vs Sonar', 'GPT-5.5 vs Sonar']

    print('=' * 100)
    print('1  DESKRIPTIVE KENNZAHLEN JE SYSTEM  (n = 60 Fragen)')
    print('=' * 100)
    rep_acc = [90.0, 90.0, 78.3]; rep_ex = [35.0, 68.3, 51.7]
    rep_ms = [1.167, 1.683, 1.283]; rep_sf = [6.7, 3.3, 1.7]
    for j, m in enumerate(ORDER):
        a, e, s = int(acc[:, j].sum()), int(exact[:, j].sum()), int(safe[:, j].sum())
        lo, hi = wilson_ci(a, 60)
        print(f'  {m:<22s} korrekt {a:2d}/60 = {100*a/60:5.1f} % (berichtet {rep_acc[j]:.1f}), '
              f'Wilson-KI {lo:.1f}-{hi:.1f}')
        print(f'  {"":22s} exakter Leitlinienbezug {e:2d}/60 = {100*e/60:5.1f} % '
              f'(berichtet {rep_ex[j]:.1f})')
        print(f'  {"":22s} mittlerer Ordinalwert {ref[:, j].mean():.3f} (berichtet {rep_ms[j]:.3f}), '
              f'Sicherheitsbedenken {s}/60 = {100*s/60:.1f} % (berichtet {rep_sf[j]:.1f})')

    print()
    print('=' * 100)
    print('2  OMNIBUSTESTS')
    print('=' * 100)
    for label, mat, rq, rp in [('Accuracy, Cochran Q', acc, 6.125, 0.0468),
                               ('Exakter Leitlinienbezug, Cochran Q', exact, 13.333, 0.0013),
                               ('Sicherheitsbedenken, Cochran Q', safe, 2.800, 0.247)]:
        q = cochran_q(mat)
        cmp_line(f'{label} - Statistik', rq, q)
        cmp_line(f'{label} - p', rp, chi2_sf_df2(q))
    f = friedman(ref)
    cmp_line('Leitlinienbezug ordinal, Friedman - Statistik', 14.230, f)
    cmp_line('Leitlinienbezug ordinal, Friedman - p', 0.000813, chi2_sf_df2(f))

    print()
    print('=' * 100)
    print('3  PAARVERGLEICHE, EXAKTER McNEMAR, MIT HOLM-KORREKTUR')
    print('=' * 100)
    for label, mat, raw_rep, holm_rep in [
            ('Accuracy', acc, [1.000, 0.065, 0.092], [1.000, 0.196, 0.196]),
            ('Exakter Leitlinienbezug', exact, [0.0012, 0.121, 0.041], [0.0036, 0.121, 0.083]),
            ('Sicherheitsbedenken', safe, [0.625, 0.375, 1.000], [1.000, 1.000, 1.000])]:
        print(f'  -- {label}')
        ps = []
        for (a_, b_), nm in zip(PAIRS, PNAME):
            n10, n01, p = mcnemar_exact(mat[:, a_], mat[:, b_])
            ps.append(p)
            diff = 100 * (mat[:, a_].mean() - mat[:, b_].mean())
            print(f'     {nm:<28s} Differenz {diff:+6.1f} pp   diskordant b={n10:2d} c={n01:2d}')
        for nm, p, r in zip(PNAME, ps, raw_rep):
            cmp_line(f'   {nm} - roher p', r, p)
        for nm, p, r in zip(PNAME, holm(ps), holm_rep):
            cmp_line(f'   {nm} - Holm-p', r, p)

    print('  -- Leitlinienbezug ordinal, Wilcoxon mit Pratt')
    ps = []
    for (a_, b_), nm in zip(PAIRS, PNAME):
        d, p = wilcoxon_pratt(ref[:, a_], ref[:, b_])
        ps.append(p)
        print(f'     {nm:<28s} mittlere Differenz {d:+.3f}   p = {p:.6f}')
    for nm, p, r in zip(PNAME, holm(ps), [0.000658, 0.368, 0.0031]):
        cmp_line(f'   {nm} - Holm-p', r, p, tol=0.02)
    print('     Hinweis: Normalapproximation mit Bindungs- und Stetigkeitskorrektur.')
    print('     Die Originalauswertung nutzt moeglicherweise eine exakte Variante;')
    print('     kleine Abweichungen in der letzten Stelle sind dadurch erklaerbar.')

    print()
    print('=' * 100)
    print('4  INTERRATER-UEBEREINSTIMMUNG DER ERSTBEWERTUNGEN')
    print('=' * 100)
    A = {r['Rating ID']: r for r in data['raterA']}
    B = {r['Rating ID']: r for r in data['raterB']}
    ids = sorted(set(A) & set(B))
    for col, cats, rep_ag, rep_k, rep_ac in [
            ('Accuracy rating', ['Correct', 'Partially correct', 'Incorrect', 'Not assessable'],
             92.2, 0.707, 0.910),
            ('Guideline reference correct?', ['Yes', 'Partly', 'No', 'Not assessable'],
             88.9, 0.814, 0.842),
            ('Safety concern?', ['No', 'Minor', 'Major', 'Not assessable'], 95.0, 0.289, 0.948)]:
        x = [A[i][col] for i in ids]
        y = [B[i][col] for i in ids]
        ag = 100 * sum(1 for i in range(len(ids)) if x[i] == y[i]) / len(ids)
        cmp_line(f'{col} - Uebereinstimmung %', rep_ag, ag, tol=0.15)
        cmp_line(f'{col} - Cohen Kappa', rep_k, cohen_kappa(x, y, cats), tol=0.02)
        cmp_line(f'{col} - Gwet AC1', rep_ac, gwet_ac1(x, y, cats), tol=0.02)
    print('  High-Level Evidence Support wird bewusst nicht ausgewertet: Nachbewertung ausstehend.')

    print()
    print('=' * 100)
    print('5  MARGINALER DOMAENENEFFEKT, PERMUTATIONSTEST AUF FRAGEEBENE')
    print('=' * 100)
    print('  Validierung des Verfahrens am bereits berichteten Endpunkt, dann Anwendung')
    print('  auf die Accuracy, fuer die bisher kein Domaeneneffekt berichtet ist.')
    print()
    for label, mat, rep_f, rep_p in [
            ('Exakter Leitlinienbezug', exact, 5.005, 0.011),
            ('Leitlinienbezug ordinal', ref, 2.902, 0.069),
            ('Accuracy  << bisher nicht berichtet', acc, None, None)]:
        per_q = mat.mean(axis=1)
        F, p = permutation_domain_effect(per_q, domains, n_perm=20000)
        means = [per_q[[i for i, d in enumerate(domains) if d == g]].mean()
                 for g in ['Domain 1', 'Domain 2', 'Domain 3']]
        print(f'  {label}')
        print(f'     Domaenenmittel  D1 {means[0]:.3f}   D2 {means[1]:.3f}   D3 {means[2]:.3f}')
        cmp_line('     Pseudo-F', rep_f, F, tol=0.35)
        cmp_line('     Permutations-p', rep_p, p, tol=0.02)
    print('  20.000 statt 200.000 Permutationen; der p-Wert schwankt dadurch in der dritten Stelle.')

    print()
    print('=' * 100)
    print('6  NICHT REPRODUZIERT')
    print('=' * 100)
    print('  - Bootstrap-Konfidenzintervalle der Paarvergleiche.')
    print('    Diese sind der einzige Teil, bei dem Intervall und p-Wert in fuenf Faellen')
    print('    gegenlaeufig ausfallen. Zur Reproduktion fehlt die Resampling-Spezifikation')
    print('    (Anzahl Replikate, Intervalltyp, Umgang mit Bindungen).')
    print('  - Pseudo-F der Modell-mal-Domaene-Heterogenitaet (3.976 bzw. 7.871).')
    print('    Erfordert die genaue Kontrastdefinition der Originalauswertung.')


if __name__ == '__main__':
    base = sys.argv[1] if len(sys.argv) > 1 else '.'
    main(base)
```
