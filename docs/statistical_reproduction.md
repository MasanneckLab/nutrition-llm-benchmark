# Statistical reproduction: where each reported figure comes from

Every figure in the manuscript (draft of 30 August 2026) maps to one script in
`analysis/`. Each script ends with a block of reference values; a run must reproduce
them. Where a figure does not reproduce from the deposited data, this is stated here
and in the script.

| Manuscript | Figure | Script |
|---|---|---|
| Methods 2.6 | intraclass correlation of the two questions of a topic, 0.752 | `supplementary_analyses.py` (1) |
| Table 3 | counts, percentages, Wilson intervals; Cochran's Q for accuracy, exact reference, safety, evidence quality; Friedman for the three-level scale | `reproduce_statistics.py` (1, 2) |
| Results 3.1 | accuracy: no pairwise contrast after Holm; knowledge versus case, odds ratios | `reproduce_statistics.py` (3), `supplementary_analyses.py` (6) |
| Results 3.1 | accuracy across domains, pseudo-F 0.565, p = 0.60 | `reproduce_statistics.py` (5) |
| Results 3.1 | inter-rater agreement, kappa, AC1 | `reproduce_statistics.py` (4) |
| Results 3.2 | safety concern: 7 of 180, 3.9 % (1.9 to 7.8) | `reproduce_statistics.py` (1, 3) |
| Results 3.3, Table 4 | sign-flip permutation p values, exact and three-level scale, Holm within scale | `01_topic_level_contrasts.py` |
| Table 4 | Cliff's delta with BCa bootstrap intervals over 30 topics | `02_cliffs_delta.py` |
| Results 3.4 | evidence quality: Holm-adjusted McNemar p = 0.003, 0.013, 0.375 | `reproduce_statistics.py` (3) |
| Results 3.7 | domain effect on exact reference, pseudo-F 5.005; domain 2 versus 3, +26.7 pp, Holm p = 0.028; system-by-domain interaction | `reproduce_statistics.py` (5), `supplementary_analyses.py` (2, 3) |
| Results 3.6, Figure 1 | grade of recommendation: 0.71 vs 1.47 (Holm p 0.0045), 1.88 vs 1.56 (0.21), 1.25 vs 1.31 (0.61); 1 of 24, 20 of 36, 21 of 24 | `figure1_by_grade.py`, `supplementary_analyses.py` (4) |
| Table 5, S5 | composition of cited sources, in-text and all extracted | `table5_citation_sources.py` |
| Results 3.5 | applicable guideline cited 0 / 52 / 28; earlier edition 0 / 38 / 8; commercial sources in 5 responses | `table5_citation_sources.py` |
| S4 | category and reason per source domain | `revise_categories.py` |
| S6, Limitations | truncated Sonar responses: 22 of 60, 18 after the answer, endpoint shifts at most 3.9 pp, contrasts with and without | `s6_truncated_responses.py`, `text_completeness.py` |

## Notes on individual figures

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

**Gwet's AC1.** Chance agreement is divided by the number of categories actually
assigned by either rater minus one: two for safety concern (0.946), three otherwise.
With the full scale the values rise by up to 0.02.

**Domain effect, Holm-adjusted p.** The manuscript gives 0.021 for the exact
reference scale; with 20,000 permutations the script gives 0.011 raw and 0.023 after
Holm over the two scales. Permutation noise in the third decimal.

## Conventions

- Seeds: 20260812 (supplementary analyses, Figure 1), 20260820 (topic-level
  contrasts, Cliff's delta, S6), 20260712 (domain effect).
- Topic-level tests: 200,000 sign-flip permutations. Grade effect: 50,000
  permutations within domains. Domain effect: 20,000 permutations at question level.
- Bootstrap: 5,000 BCa resamples over topics.
- Holm correction within each family of three contrasts, or over the three systems
  for the grade effect, or over the two scales for the domain effect.
- All tests that compare systems on guideline reference use the 30 topic means.
  Tests at question level (McNemar, Cochran's Q, Friedman) treat the 60 questions as
  independent; the manuscript uses them for the omnibus tests and for the endpoints
  other than guideline reference.
