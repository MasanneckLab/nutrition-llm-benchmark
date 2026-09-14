# Independent verification, 14 September 2026

The checks in `verification/verify_key_results.py` were written independently of
the analysis functions in `analysis/`. They start from the deposited CSV files,
rebuild the question and topic structure, and use exact enumeration where this is
feasible.

## Five requested results

| Requested result | Independent result | Assessment |
|---|---:|---|
| Correct answers, Open Evidence / GPT-5.5 / Sonar Reasoning Pro | 54 / 54 / 47 of 60 | confirmed |
| Exact guideline reference | 21 / 41 / 31 of 60 | confirmed |
| Rater agreement: accuracy / reference / evidence / safety | 92.2 / 88.9 / 88.3 / 95.0% | confirmed |
| GPT-5.5 minus Open Evidence, exact reference | +33.3 percentage points; exact Holm p = 0.0373 | confirms the reported seeded estimate of p = 0.0381 |
| Open Evidence, evidence-graded versus GPP | 1/24 versus 20/36 exact references; exact stratified Holm p = 0.0035 | confirms the reported seeded estimate of p = 0.0045 |

For the last result, the count is descriptive. The p value tests the ordinal
guideline-reference score at topic level, with recommendation grade permuted within
clinical domain. It is not a direct comparison of the two response-level
proportions.

## Data checks

- `answers_v2.csv` has 180 unique model-question rows: 60 per system.
- `ratings_raters.csv` has the same 180 rating IDs and reconciles exactly with all
  four consensus columns in `answers_v2.csv`.
- `items_master.csv` has 60 unique questions and reconciles exactly with accuracy,
  guideline-reference and safety ratings for all three systems.
- Every system has two responses for each of 30 topics.
- The July consensus workbook and both individual rater workbooks on the local
  project drive reconcile exactly with the deposited accuracy, guideline-reference
  and safety fields. The later evidence-quality rerating is only available here as
  the deposited derived table, so its arithmetic was checked but its workbook-level
  provenance could not be checked independently.
- Fifteen answer hashes differ between the current July consensus workbook and the
  private build key because that key predates the documented correction of 13
  sources-only Sonar exports. Against the corrected sources, 178/180 answer texts
  match after formatting normalization; the remaining two are near-identical and
  contain spreadsheet cell-reference tokens. This does not alter rating linkage,
  the ratings or citation counts, but the private key should be regenerated before
  archival. Raw answer texts and the key remain private.
- The citation extraction chain reproduces 431 / 168 / 876 extracted citations
  before document merging and 1,462 rows after merging. The validator reports one
  known duplicate-counting convention and no missing citations.

## Correction made during the check

The completeness detector treated a GPT-5.5 answer ending in a period followed by
a curly closing double quote as truncated. The underlying Batch record has
`finish_reason="stop"` and the answer ends normally. The terminal-character rule
was corrected. The resulting count is 22/60 truncated Sonar Reasoning Pro answers
and 0/60 truncated GPT-5.5 answers.

For the Sonar run, the collection code did not retain `finish_reason` or token
usage. The original 22 full responses cannot be reconstructed from the current
files; the stored outputs are the complete evidence available for analysis.

There is a separate acquisition caveat. Thirteen initial Sonar exports contained
only a source list and were replaced before rating by new calls with
`max_tokens=8000`; the initial run used `3000`. None of the 13 replacements is in
the 22 truncated-answer set. In the final ratings, the replacements had 12/13
correct and 9/13 exact-reference answers, compared with 35/47 and 22/47 among the
retained initial answers. These are descriptive, selected groups, not a valid
causal comparison. The mixed run settings and replacement rule should be reported
in the Methods and considered when interpreting Sonar performance and truncation.

## Domain-effect sensitivity

The manuscript analysis of a marginal domain effect averages across systems but
permutes domain labels over 60 question rows. The data themselves show that the two
questions from one recommendation are correlated and should be treated as one
topic.

Repeating the domain analysis over 30 topic means gives the same exact-reference
means (Domain 1: 0.550, Domain 2: 0.633, Domain 3: 0.367), but weaker inference:

- the topic-level omnibus permutation p value is about 0.029 for exact reference;
- after Holm correction over the exact and ordinal scales, p is about 0.058;
- Domain 2 versus Domain 3 is +26.7 percentage points, exact raw p = 0.0240 and
  Holm p = 0.0719 across the three domain pairs.

The domain pattern is real descriptively, but the claim of a statistically
significant adjusted domain difference is sensitive to treating paired questions
as independent. It should be described as exploratory unless a prespecified
cluster-aware model supports the stronger wording.

## Other topic-level sensitivities

The same issue affects the nominal accuracy omnibus result. Cochran's Q over 60
question rows gives p = 0.0468. An exact test that first averages the two questions
within each of the 30 topics and then permutes system labels within topic gives
p = 0.0950. The model percentages are unchanged and all pairwise accuracy contrasts
remain non-significant, but the manuscript should not call the accuracy difference
robustly significant.

The corresponding exact topic-level omnibus tests remain significant for evidence
quality (p = 0.00035) and non-significant for safety concerns (p = 0.333). The
evidence-quality pairwise conclusions also remain significant after Holm correction.
