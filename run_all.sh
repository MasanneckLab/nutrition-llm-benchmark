#!/bin/sh
# Runs every analysis that works from the deposited data in data/.
# The citation extraction and the two text checks need the rating workbooks,
# which are not deposited; for those set  export NUTRITION_RAW=/path/to/raw/data
set -e
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON=${PYTHON:-"$ROOT/.venv/bin/python"}

if [ ! -x "$PYTHON" ]; then
  echo "Python environment not found at $PYTHON" >&2
  echo "Create it with: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt" >&2
  exit 1
fi

cd "$ROOT/analysis"

echo "== Table 3, topic-level tests, agreement, domain effect =="
"$PYTHON" reproduce_statistics.py
echo; echo "== Table 4: topic-level contrasts =="
"$PYTHON" 01_topic_level_contrasts.py
echo; echo "== Table 4: Cliff's delta with bootstrap intervals =="
"$PYTHON" 02_cliffs_delta.py
echo; echo "== ICC, model-by-domain heterogeneity, grade effect, odds ratios =="
"$PYTHON" supplementary_analyses.py
echo; echo "== Figure 1 =="
"$PYTHON" figure1_by_grade.py
echo; echo "== Category revision (S4) =="
"$PYTHON" revise_categories.py
echo; echo "== Table 5 and S5 =="
"$PYTHON" table5_citation_sources.py
echo; echo "== S6: truncated responses =="
"$PYTHON" s6_truncated_responses.py
echo; echo "== Accuracy and citation behaviour =="
"$PYTHON" accuracy_citation_crosstab.py
echo; echo "== ESPEN mentions =="
"$PYTHON" espen_mentions.py

echo; echo "== Independent reconstruction of the central results =="
"$PYTHON" ../verification/verify_key_results.py

if [ -n "$NUTRITION_RAW" ]; then
  echo; echo "== Citation extraction chain (raw data) =="
  "$PYTHON" extract_citations.py
  "$PYTHON" classify_citations.py
  "$PYTHON" build_long_table.py
  "$PYTHON" merge_documents.py
  echo; echo "== In-text citations (raw data) =="
  "$PYTHON" in_text_citations.py
  echo; echo "== Text completeness (raw data) =="
  "$PYTHON" text_completeness.py
  echo; echo "== Validation of the extraction (raw data) =="
  "$PYTHON" validate_extraction.py || true
else
  echo; echo "Extraction chain, in-text assignment, text completeness and validation skipped: NUTRITION_RAW is not set."
fi
