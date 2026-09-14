# Query collection

This folder contains the code used to collect the model answers before rating.
The prompt is in `Nutrition/prompt.md`, and the three source workbooks are in
`Nutrition/source_workbooks/`.

The final manuscript data use Sonar Reasoning Pro and GPT-5.5. The same Perplexity
run also collected Sonar and Sonar Pro answers, but those two systems are not part
of the final three-system analysis.

## Perplexity

The initial collection run used one call per question and model, temperature 0.2,
`max_tokens=3000`, and no domain whitelist.

```bash
../.venv/bin/python Nutrition/perplexity_nutrition_export.py --dry-run
../.venv/bin/python Nutrition/perplexity_nutrition_export.py \
  --models sonar sonar-pro sonar-reasoning-pro \
  --iterations 1 --temperature 0.2 --max-tokens 3000
```

The original exporter saved the returned answer and citations but did not retain
the API `finish_reason` or token usage. Those fields therefore cannot be recovered
retrospectively for the June 2026 Sonar run.

Thirteen Sonar Reasoning Pro exports contained a source list but no usable answer.
They were replaced before rating by new calls on 21 July 2026 with temperature 0.2
and `max_tokens=8000`. The final analyzed Sonar sample therefore contains 47
answers from the initial run and 13 replacement answers. The replacement IDs and
settings, but not the private answer texts, are recorded in
`replacement_queries.json`.

## OpenAI Batch

GPT-5.5 was queried in one batch of 60 requests. The run used no explicit
temperature, `max_completion_tokens=3000`, and a 24-hour completion window.

```bash
../.venv/bin/python Nutrition/openai_batch_nutrition.py prepare \
  --model gpt-5.5 --max-tokens 3000
../.venv/bin/python Nutrition/openai_batch_nutrition.py submit --run-dir PATH
../.venv/bin/python Nutrition/openai_batch_nutrition.py materialize --run-dir PATH
```

`prepare` is offline. `submit` and `materialize` call the API.

## Open Evidence

The 60 Open Evidence answers were exported manually and then brought into the same
workbook format. There is no Open Evidence API script in this repository.

The exact settings used for the selected systems are also recorded in
`run_parameters.json`.
