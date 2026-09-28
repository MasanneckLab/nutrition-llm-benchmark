# Statistical reproduction: where each reported figure comes from

Every figure in the manuscript (state of 20 September 2026) maps to one script in
`analysis/`. Each script ends with a block of reference values; a run must reproduce
them. Where a figure does not reproduce from the deposited data, this is stated here
and in the script.

| Manuscript | Figure | Script |
|---|---|---|
| Methods 2.6 | intraclass correlation of the two questions of a topic, 0.752 | `supplementary_analyses.py` (1) |
| Table 3 | counts, percentages, Wilson intervals; omnibus permutation p per endpoint over the 30 topic means | `reproduce_statistics.py` (1, 2) |
| Results 3.1 | accuracy: no pairwise contrast after Holm; knowledge versus case, odds ratios | `reproduce_statistics.py` (3), `supplementary_analyses.py` (6) |
| Results 3.1 | accuracy across domains, pseudo-F 0.381, p = 0.73 | `reproduce_statistics.py` (5) |
| Results 3.1 | inter-rater agreement, kappa, AC1 | `reproduce_statistics.py` (4) |
| Results 3.2 | safety concern: 7 of 180, 3.9 % (1.9 to 7.8) | `reproduce_statistics.py` (1, 3) |
| Results 3.3, Table 4 | sign-flip permutation p values, exact and three-level scale, Holm within scale | `01_topic_level_contrasts.py` |
| Table 4 | Cliff's delta with BCa bootstrap intervals over 30 topics | `02_cliffs_delta.py` |
| Results 3.4 | evidence quality: Holm-adjusted pairwise p = 0.009, 0.022, 0.501 | `reproduce_statistics.py` (3) |
| Results 3.7 | domain effect on exact reference, pseudo-F 4.178, Holm p = 0.058; domain 2 versus 3, +26.7 pp, Holm p = 0.073; system-by-domain interaction | `reproduce_statistics.py` (5), `supplementary_analyses.py` (2, 3) |
| Results 3.6, Figure 1 | grade of recommendation: 0.71 vs 1.47 (Holm p 0.004), 1.88 vs 1.56 (0.21), 1.25 vs 1.31 (0.61); 1 of 24, 20 of 36, 21 of 24 | `figure1_by_grade.py`, `supplementary_analyses.py` (4) |
| Table 5, S5 | composition of cited sources, in-text and all extracted | `table5_citation_sources.py` |
| Results 3.5 | applicable guideline cited 0 / 52 / 28; earlier edition 0 / 38 / 8; commercial sources in 5 responses | `table5_citation_sources.py` |
| Results 3.5 | ESPEN named in the body text of 142 of 180 responses (Open Evidence 49), 58 of them without exact guideline reference; no ESPEN guideline cited by Open Evidence | `espen_mentions.py` |
| S4 | category and reason per source domain | `revise_categories.py` |
| Results 3.1, Discussion | of the 25 not fully correct responses: guideline identifiable in ten, earlier edition in eight, five of them GPT-5.5 (the five the Discussion refers to) | `accuracy_citation_crosstab.py` |
| S6, Limitations | truncated Sonar responses: 22 of 60, 18 after the answer, endpoint shifts at most 3.9 pp, contrasts with and without | `s6_truncated_responses.py`, `text_completeness.py` |

## Notes on individual figures

**All system comparisons run over the 30 topic means.** Since 8 September this holds
for every endpoint, not only for guideline reference. The omnibus test permutes the
three system labels within each topic (statistic: sum of squared deviations of the
system means from the grand mean, 200,000 permutations) and replaces Cochran's Q and
the Friedman test; the pairwise contrasts are sign-flip permutations over the 30
paired topic-mean differences and replace the exact McNemar test; the domain effect
uses the per-topic mean over the three systems. The question-level values these
replace, for the record: accuracy 0.047, exact reference 0.001, safety 0.247 and
evidence quality < 0.001 for the omnibus; 0.375 / 0.003 / 0.013 for evidence quality
pairwise; 0.021 for the domain effect and 0.028 for domain 2 versus 3. Accuracy and
the domain effect are no longer significant under the topic-level tests.

**The omnibus p for the exact guideline reference sits on a rounding boundary.**
Across seeds the estimate runs from 0.0054 to 0.0058, so the third decimal is Monte
Carlo noise and the value rounds to 0.005 or 0.006 depending on the seed. The
manuscript reports 0.006; p < 0.01 is the statement that holds regardless of the
seed. The seeds in `reproduce_statistics.py` are fixed for this reason, so that the
reference block reproduces exactly rather than shifting in the third decimal from run
to run.

**Table 5 and S5.** The category revision applies the manuscript's definition of
non-scientific sources (Methods 2.5): eighteen domains that the PubMed-based rule had
placed in F count as independent evidence. This gives the reported 54.0 %, 22.8 % and
33 responses for Sonar Reasoning Pro in Table 5. The sensitivity analysis over all
extracted citations (S5) gives 38.6 % non-scientific citations in 56 responses under
the same revision, as deposited.

**Inter-rater agreement, evidence quality.** The rater columns in
`data/ratings_raters.csv` are the ratings of the second round, after the construct
had been clarified: rated is the quality of the sources the response cites, not the
grade of the guideline recommendation. The first round, in which one rater had
applied the latter reading, agreed in 13 of 180 cases; those columns are not
deposited.

**Grade of recommendation.** Holm-adjusted p for Open Evidence is 0.0036 with 200,000
permutations within domains, reported as 0.004. An earlier run with 50,000 permutations
gave 0.0045; the number of permutations now matches the Methods and every other
permutation test in the analysis.

**ESPEN in the body text.** The count uses the response text without its source
apparatus and without bracketed citations, so it measures what a system names in its
own words. An earlier search gave 117 of 180 and 42, with a different separation of
body text and citations; the 49 for Open Evidence is unchanged. The three reference
entries of Open Evidence that name ESPEN are a symposium report and two expert group
recommendations, none of them a guideline.

**Gwet's AC1.** Chance agreement is divided by the number of categories actually
assigned by either rater minus one: two for safety concern (0.946), three otherwise.
With the full scale the values rise by up to 0.02.

**Domain effect, Holm-adjusted p.** The manuscript gives 0.058 for the exact
reference scale and 0.073 for domain 2 versus 3; with the fixed seed and 200,000
permutations the script gives 0.057 and 0.072. As with the omnibus above, the third
decimal is Monte Carlo noise; neither value is significant under either reading.

## Conventions

- Seeds: 20260812 (supplementary analyses, Figure 1), 20260820 (omnibus and
  topic-level contrasts, Cliff's delta, S6), 20260712 (domain effect).
- Topic-level tests: 200,000 permutations, both for the omnibus and for the
  sign-flip contrasts. Grade effect: 200,000 permutations within domains. Domain
  effect: 200,000 permutations over the 30 topic values.
- Bootstrap: 5,000 BCa resamples over topics.
- Holm correction within each family of three contrasts, or over the three systems
  for the grade effect, or over the two scales for the domain effect.
- All tests that compare systems use the 30 topic means. The counts and Wilson
  intervals of Table 3 remain response-level (n = 60 per system); they describe the
  data and are not tests.
