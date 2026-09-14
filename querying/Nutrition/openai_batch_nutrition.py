from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from openai import OpenAI

REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from perplexity_experiment import (  # noqa: E402
    discover_nutrition_workbooks,
    export_nutrition_results_workbooks,
    load_all_nutrition_questions,
    load_prompt_text,
)

NUTRITION_DIR = Path(__file__).resolve().parent
SOURCE_WORKBOOKS_DIR = NUTRITION_DIR / "source_workbooks"
DEFAULT_OUTPUT_DIR = NUTRITION_DIR / "model_outputs" / "openai"
RUNS_DIR = NUTRITION_DIR / "openai_batch_runs"
ENV_FILENAMES = (".env", ".env.local", ".env.secret", ".envrc")
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_TEMPERATURE = None
DEFAULT_MAX_TOKENS = 3000
DEFAULT_COMPLETION_WINDOW = "24h"
DEFAULT_PROMPT_PATH = NUTRITION_DIR / "prompt.md"
LATEST_RUN_PATH = RUNS_DIR / "latest_run.json"


def _parse_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def get_openai_api_key(search_dir: Path | None = None) -> str:
    env_value = os.getenv("OPENAI_API_KEY")
    if env_value:
        return env_value

    base_dir = (search_dir or REPO_DIR).resolve()
    for directory in (base_dir, *base_dir.parents):
        for filename in ENV_FILENAMES:
            values = _parse_env_file(directory / filename)
            if values.get("OPENAI_API_KEY"):
                return values["OPENAI_API_KEY"]

    raise ValueError("OPENAI_API_KEY not found in environment or local env files.")


def make_client() -> OpenAI:
    return OpenAI(api_key=get_openai_api_key(NUTRITION_DIR))


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def json_dump(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")


def json_load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def response_text_from_choice(message_content: Any) -> str:
    if isinstance(message_content, str):
        return message_content.strip()
    if isinstance(message_content, list):
        chunks = []
        for item in message_content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(str(item.get("text", "")))
        return "\n".join(chunk for chunk in chunks if chunk).strip()
    return str(message_content or "").strip()


def model_output_suffix(model: str) -> str:
    model_slug = model.replace(".", "").replace("-", "")
    return f"_openai_{model_slug}_batch"


def build_request_body(
    system_prompt: str,
    question: str,
    model: str,
    temperature: float | None,
    max_tokens: int,
) -> dict[str, Any]:
    body = {
        "model": model,
        "max_completion_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    }
    if temperature is not None:
        body["temperature"] = temperature
    return body


def create_run(
    nutrition_dir: Path = SOURCE_WORKBOOKS_DIR,
    prompt_path: Path = DEFAULT_PROMPT_PATH,
    model: str = DEFAULT_MODEL,
    temperature: float | None = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> Path:
    nutrition_dir = Path(nutrition_dir).resolve()
    prompt_path = Path(prompt_path).resolve()
    prompt_text = load_prompt_text(prompt_path)
    questions = load_all_nutrition_questions(nutrition_dir)
    source_workbooks = discover_nutrition_workbooks(nutrition_dir)

    run_dir = RUNS_DIR / f"{timestamp_slug()}_{model.replace('.', '_')}"
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries = []
    request_lines = []
    for index, question_row in enumerate(questions, start=1):
        custom_id = f"nutrition-row-{index:03d}"
        manifest_entries.append(
            {
                "custom_id": custom_id,
                "source_workbook": question_row["source_workbook"],
                "sheet_name": question_row["sheet_name"],
                "row_index": question_row["row_index"],
                "question_row": question_row,
            }
        )
        request_lines.append(
            {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": build_request_body(
                    system_prompt=prompt_text,
                    question=str(question_row["Question"]),
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
            }
        )

    request_path = run_dir / "requests.jsonl"
    with request_path.open("w", encoding="utf-8") as handle:
        for line in request_lines:
            handle.write(json.dumps(line, ensure_ascii=True) + "\n")

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "nutrition_dir": str(nutrition_dir),
        "source_workbooks": [str(path.resolve()) for path in source_workbooks],
        "prompt_path": str(prompt_path),
        "request_path": str(request_path),
        "question_count": len(questions),
        "output_suffix": model_output_suffix(model),
        "entries": manifest_entries,
    }
    json_dump(manifest, run_dir / "manifest.json")
    json_dump(
        {
            "run_dir": str(run_dir),
            "model": model,
            "question_count": len(questions),
            "created_at": manifest["created_at"],
        },
        LATEST_RUN_PATH,
    )
    return run_dir


def upload_batch_input(client: OpenAI, request_path: Path) -> dict[str, Any]:
    with request_path.open("rb") as handle:
        upload = client.files.create(file=handle, purpose="batch")
    return upload.model_dump(mode="json")


def create_batch(
    client: OpenAI,
    input_file_id: str,
    model: str,
    completion_window: str = DEFAULT_COMPLETION_WINDOW,
) -> dict[str, Any]:
    batch = client.batches.create(
        input_file_id=input_file_id,
        endpoint="/v1/chat/completions",
        completion_window=completion_window,
        metadata={
            "project": "nutrition",
            "model": model,
            "workflow": "openai-batch-no-tools",
        },
    )
    return batch.model_dump(mode="json")


def submit_run(run_dir: Path) -> dict[str, Any]:
    manifest = json_load(run_dir / "manifest.json")
    client = make_client()
    request_path = Path(manifest["request_path"])
    input_file_path = run_dir / "input_file.json"

    if input_file_path.exists():
        upload_payload = json_load(input_file_path)
    else:
        upload_payload = upload_batch_input(client, request_path)
        json_dump(upload_payload, input_file_path)

    batch_payload = create_batch(
        client=client,
        input_file_id=upload_payload["id"],
        model=manifest["model"],
    )
    json_dump(batch_payload, run_dir / "batch.json")

    json_dump(
        {
            "run_dir": str(run_dir),
            "batch_id": batch_payload["id"],
            "model": manifest["model"],
            "question_count": manifest["question_count"],
            "created_at": manifest["created_at"],
        },
        LATEST_RUN_PATH,
    )
    return batch_payload


def resolve_run_dir(run_dir: str | None) -> Path:
    if run_dir:
        return Path(run_dir).resolve()
    if not LATEST_RUN_PATH.exists():
        raise FileNotFoundError("No latest run metadata found. Create or submit a run first.")
    latest = json_load(LATEST_RUN_PATH)
    return Path(latest["run_dir"]).resolve()


def retrieve_batch(run_dir: Path) -> dict[str, Any]:
    batch_payload = json_load(run_dir / "batch.json")
    client = make_client()
    refreshed = client.batches.retrieve(batch_payload["id"]).model_dump(mode="json")
    json_dump(refreshed, run_dir / "batch_status.json")
    return refreshed


def download_file_content(file_id: str, output_path: Path) -> Path:
    api_key = get_openai_api_key(NUTRITION_DIR)
    response = requests.get(
        f"https://api.openai.com/v1/files/{file_id}/content",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=300,
    )
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return output_path


def download_batch_artifacts(run_dir: Path) -> dict[str, Path]:
    status_payload = retrieve_batch(run_dir)
    downloaded: dict[str, Path] = {}

    output_file_id = status_payload.get("output_file_id")
    if output_file_id:
        downloaded["output"] = download_file_content(
            output_file_id, run_dir / "output.jsonl"
        )

    error_file_id = status_payload.get("error_file_id")
    if error_file_id:
        downloaded["error"] = download_file_content(
            error_file_id, run_dir / "errors.jsonl"
        )

    return downloaded


def load_jsonl_by_custom_id(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return records

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        custom_id = payload.get("custom_id")
        if custom_id:
            records[custom_id] = payload
    return records


def export_from_downloads(
    run_dir: Path,
    output_dir: Path | None = None,
    output_suffix: str | None = None,
) -> dict[str, str]:
    manifest = json_load(run_dir / "manifest.json")
    output_records = load_jsonl_by_custom_id(run_dir / "output.jsonl")
    error_records = load_jsonl_by_custom_id(run_dir / "errors.jsonl")

    rows = []
    for entry in manifest["entries"]:
        custom_id = entry["custom_id"]
        question_row = dict(entry["question_row"])
        source_workbook = Path(question_row["source_workbook"])
        if not source_workbook.exists():
            relocated_source = SOURCE_WORKBOOKS_DIR / source_workbook.name
            if not relocated_source.exists():
                raise FileNotFoundError(
                    f"Source workbook not found at {source_workbook} or {relocated_source}"
                )
            question_row["source_workbook"] = str(relocated_source.resolve())
        output_record = output_records.get(custom_id)
        error_record = error_records.get(custom_id)

        answer = None
        model_name = manifest["model"]
        if output_record:
            response_body = (output_record.get("response") or {}).get("body") or {}
            choices = response_body.get("choices") or []
            if choices:
                message = choices[0].get("message") or {}
                answer = response_text_from_choice(message.get("content"))
            model_name = response_body.get("model") or model_name
        elif error_record:
            response_error = (
                ((error_record.get("response") or {}).get("body") or {}).get("error")
                or {}
            )
            top_level_error = error_record.get("error") or {}
            answer = f"ERROR: {response_error.get('message') or top_level_error.get('message') or 'Unknown batch error'}"
        else:
            answer = "ERROR: Missing batch output for this request."

        rows.append(
            {
                **question_row,
                "Model": model_name,
                "Model Answer": answer,
            }
        )

    exported = export_nutrition_results_workbooks(
        rows=rows,
        suffix=output_suffix or manifest.get("output_suffix") or model_output_suffix(manifest["model"]),
        output_dir=output_dir,
    )
    json_dump(
        {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "output_workbooks": exported,
            "row_count": len(rows),
        },
        run_dir / "export.json",
    )
    return exported


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare, submit, and materialize an OpenAI Batch run for Nutrition questions."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="Create batch input artifacts.")
    prepare_parser.add_argument("--nutrition-dir", default=str(SOURCE_WORKBOOKS_DIR))
    prepare_parser.add_argument("--prompt-path", default=str(DEFAULT_PROMPT_PATH))
    prepare_parser.add_argument("--model", default=DEFAULT_MODEL)
    prepare_parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    prepare_parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)

    submit_parser = subparsers.add_parser("submit", help="Prepare and submit a new batch.")
    submit_parser.add_argument("--run-dir")
    submit_parser.add_argument("--nutrition-dir", default=str(SOURCE_WORKBOOKS_DIR))
    submit_parser.add_argument("--prompt-path", default=str(DEFAULT_PROMPT_PATH))
    submit_parser.add_argument("--model", default=DEFAULT_MODEL)
    submit_parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    submit_parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)

    status_parser = subparsers.add_parser("status", help="Refresh batch status for a run.")
    status_parser.add_argument("--run-dir")

    download_parser = subparsers.add_parser("download", help="Download batch output/error files.")
    download_parser.add_argument("--run-dir")

    export_parser = subparsers.add_parser(
        "export",
        help="Export downloaded batch results into the Nutrition workbook format.",
    )
    export_parser.add_argument("--run-dir")
    export_parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    export_parser.add_argument("--output-suffix")

    materialize_parser = subparsers.add_parser(
        "materialize",
        help="Refresh status, download any files, and export workbooks if available.",
    )
    materialize_parser.add_argument("--run-dir")
    materialize_parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    materialize_parser.add_argument("--output-suffix")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.command == "prepare":
        run_dir = create_run(
            nutrition_dir=Path(args.nutrition_dir),
            prompt_path=Path(args.prompt_path),
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        print(run_dir)
        return 0

    if args.command == "submit":
        run_dir = (
            resolve_run_dir(args.run_dir)
            if args.run_dir
            else create_run(
                nutrition_dir=Path(args.nutrition_dir),
                prompt_path=Path(args.prompt_path),
                model=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )
        )
        try:
            batch_payload = submit_run(run_dir)
        except Exception as exc:
            json_dump(
                {
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "run_dir": str(run_dir),
                    "error": str(exc),
                },
                run_dir / "submit_error.json",
            )
            print(f"run_dir={run_dir}")
            print(f"error={exc}")
            return 1
        print(f"run_dir={run_dir}")
        print(f"batch_id={batch_payload['id']}")
        print(f"status={batch_payload['status']}")
        return 0

    if args.command == "status":
        run_dir = resolve_run_dir(args.run_dir)
        payload = retrieve_batch(run_dir)
        print(f"run_dir={run_dir}")
        print(f"batch_id={payload['id']}")
        print(f"status={payload['status']}")
        return 0

    if args.command == "download":
        run_dir = resolve_run_dir(args.run_dir)
        downloaded = download_batch_artifacts(run_dir)
        print(f"run_dir={run_dir}")
        for key, value in downloaded.items():
            print(f"{key}_path={value}")
        return 0

    if args.command == "export":
        run_dir = resolve_run_dir(args.run_dir)
        exported = export_from_downloads(
            run_dir,
            output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
            output_suffix=args.output_suffix,
        )
        for source_workbook, output_workbook in exported.items():
            print(f"{source_workbook} -> {output_workbook}")
        return 0

    if args.command == "materialize":
        run_dir = resolve_run_dir(args.run_dir)
        payload = retrieve_batch(run_dir)
        print(f"run_dir={run_dir}")
        print(f"batch_id={payload['id']}")
        print(f"status={payload['status']}")
        downloaded = download_batch_artifacts(run_dir)
        for key, value in downloaded.items():
            print(f"{key}_path={value}")
        if downloaded or (run_dir / "output.jsonl").exists() or (run_dir / "errors.jsonl").exists():
            exported = export_from_downloads(
                run_dir,
                output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
                output_suffix=args.output_suffix,
            )
            for source_workbook, output_workbook in exported.items():
                print(f"{source_workbook} -> {output_workbook}")
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
