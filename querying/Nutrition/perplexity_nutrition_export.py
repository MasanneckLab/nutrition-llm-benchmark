from __future__ import annotations

import argparse
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "perplexity_experiment.py").exists():
            return candidate
    raise FileNotFoundError("Could not locate repository root containing perplexity_experiment.py")


REPO_DIR = find_repo_root(Path(__file__).resolve())
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from perplexity_experiment import (  # noqa: E402
    discover_nutrition_workbooks,
    load_all_nutrition_questions,
    run_nutrition_export,
)


NUTRITION_DIR = Path(__file__).resolve().parent
SOURCE_WORKBOOKS_DIR = NUTRITION_DIR / "source_workbooks"
DEFAULT_OUTPUT_DIR = NUTRITION_DIR / "model_outputs" / "perplexity"
DEFAULT_PROMPT_PATH = NUTRITION_DIR / "prompt.md"
DEFAULT_MODELS = ("sonar", "sonar-pro", "sonar-reasoning-pro")
DEFAULT_OUTPUT_SUFFIX = "_perplexity_sonar_reasoning"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Perplexity exports for all Nutrition domain workbooks."
    )
    parser.add_argument("--nutrition-dir", default=str(SOURCE_WORKBOOKS_DIR))
    parser.add_argument("--prompt-path", default=str(DEFAULT_PROMPT_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-suffix", default=DEFAULT_OUTPUT_SUFFIX)
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=3000)
    parser.add_argument("--whitelist", nargs="*")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print discovered workbooks/questions without calling the API.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    nutrition_dir = Path(args.nutrition_dir).resolve()
    prompt_path = Path(args.prompt_path).resolve()

    workbooks = discover_nutrition_workbooks(nutrition_dir)
    questions = load_all_nutrition_questions(nutrition_dir)

    print(f"Repo dir: {REPO_DIR}")
    print(f"Nutrition dir: {nutrition_dir}")
    print(f"Prompt path: {prompt_path}")
    print(f"Source workbooks: {len(workbooks)}")
    for workbook in workbooks:
        workbook_question_count = sum(
            1 for question in questions if Path(question["source_workbook"]) == workbook.resolve()
        )
        print(f"- {workbook.name}: {workbook_question_count} questions")
    print(f"Total questions: {len(questions)}")
    print(f"Models: {', '.join(args.models)}")
    print(f"Iterations: {args.iterations}")
    print(f"Temperature: {args.temperature}")
    print(f"Max tokens: {args.max_tokens}")
    print(f"Whitelist: {args.whitelist}")

    if args.dry_run:
        return 0

    exported = run_nutrition_export(
        nutrition_dir=nutrition_dir,
        prompt_path=prompt_path,
        output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
        output_suffix=args.output_suffix,
        models=args.models,
        iterations=args.iterations,
        whitelist=args.whitelist,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    for source_workbook, output_workbook in exported.items():
        print(f"{source_workbook} -> {output_workbook}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
