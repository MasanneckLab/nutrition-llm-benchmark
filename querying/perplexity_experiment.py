import logging
import os
import re
from copy import copy
from pathlib import Path
from urllib.parse import urlparse

import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)

API_ENDPOINT = "https://api.perplexity.ai/chat/completions"
DEFAULT_TIMEOUT = 120
THINKING_PATTERN = re.compile(r"<think>\s*(.*?)\s*</think>", re.DOTALL | re.IGNORECASE)
ENV_FILENAMES = (".env", ".env.local", ".env.secret", ".envrc")

DEFAULT_SYSTEM_PROMPT = """You are a dedicated AI medical assistant specializing in
neurology. Your answers should be based on medical guidelines such as the most
recent AAN guidelines and are strictly truthful. If the information is not
available in guidelines, state it clearly. Refrain from including irrelevant or
out-of-context details.
Please respond to the following question using information from guidelines.
Focus on providing answers that are:
    - Directly linked to the guidelines, citing specific sections or page
      numbers when possible. Make sure to mention the guidelines you are
      referencing and the source.
    - Presented in concise bullet points. Do not bloat the answer
      unnecessarily. Keep it short and professional.
    - Comprehensive, including all relevant details about disease type,
      disease stage, patient age, and clinical trials when applicable.
    - Honest, clearly stating if the information is not covered in the
      guidelines.
    - Including citations to the guidelines or other reputable sources
      as needed.
Based on guidelines such as the most recent AAN guidelines, provide a
detailed and truthful response that addresses the specifics of the question.
Ensure all relevant medical and scientific details are included to support
your answer."""

DYS_PHAGIA_COLUMN_MAP = {
    "Category": 1,
    "Question number": 2,
    "Type": 3,
    "Question": 4,
    "Sample Answer According to Guideline": 5,
    "Guideline": 6,
    "model": 7,
    "whitelist": 8,
    "batch": 9,
    "Thinking": 10,
    "Answer": 11,
}

RATING_START_COLUMN = 12
RATING_END_COLUMN = 29

NUTRITION_HEADER_ALIASES = {
    "Recommendation/section": "Recommendation",
    "Exact guideline quote": "Exact quote",
}
NUTRITION_INPUT_FIELDS = [
    "Nr",
    "Question type",
    "Guideline",
    "Page",
    "Recommendation",
    "Exact quote",
    "Question",
    "Reference answer",
]
NUTRITION_RESULT_FIELDS = ["Model", "Model Answer"]
NUTRITION_GENERATED_MARKERS = ("_perplexity_", "_openai_", "_synthetic_")
PROMPT_TEXT_REPLACEMENTS = {
    "\u201c": '"',
    "\u201d": '"',
    "\u2018": "'",
    "\u2019": "'",
    "\u2013": "-",
    "\u2014": "-",
}


def _parse_env_file(env_path: Path) -> dict:
    values = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        values[key] = value
    return values


def get_perplexity_api_key(search_dir: str | os.PathLike | None = None) -> str:
    for env_name in ("PERPLEXITY_API_KEY", "PPLX_API_KEY"):
        env_value = os.getenv(env_name)
        if env_value:
            return env_value

    base_dir = Path(search_dir or Path.cwd()).resolve()
    for directory in (base_dir, *base_dir.parents):
        for filename in ENV_FILENAMES:
            env_value = _parse_env_file(directory / filename)
            for env_name in ("PERPLEXITY_API_KEY", "PPLX_API_KEY"):
                if env_value.get(env_name):
                    return env_value[env_name]

    raise ValueError(
        "PERPLEXITY_API_KEY not found in environment variables or local env files."
    )


def load_prompt_text(prompt_path: str | os.PathLike) -> str:
    return Path(prompt_path).read_text(encoding="utf-8").strip()


def normalize_prompt_text(prompt_text: str) -> str:
    normalized = prompt_text
    for old, new in PROMPT_TEXT_REPLACEMENTS.items():
        normalized = normalized.replace(old, new)
    return normalized


def extract_prompt_text_from_docx(prompt_docx_path: str | os.PathLike) -> str:
    from docx import Document

    document = Document(prompt_docx_path)
    paragraphs = [
        normalize_prompt_text(paragraph.text.strip())
        for paragraph in document.paragraphs
    ]
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]

    if paragraphs and paragraphs[0].lower() == "prompt":
        paragraphs = paragraphs[1:]
    if paragraphs and paragraphs[-1].rstrip(":").lower() == "question":
        paragraphs = paragraphs[:-1]

    return "\n\n".join(paragraphs).strip()


def write_prompt_markdown_from_docx(
    prompt_docx_path: str | os.PathLike,
    output_path: str | os.PathLike,
) -> str:
    prompt_text = extract_prompt_text_from_docx(prompt_docx_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(prompt_text + "\n", encoding="utf-8")
    return str(output)


def normalize_domain_filter(whitelist: list | tuple | None) -> list | None:
    if not whitelist:
        return None

    normalized = []
    seen = set()
    for entry in whitelist:
        if entry is None:
            continue
        text = str(entry).strip()
        if not text:
            continue

        prefix = ""
        if text.startswith("-"):
            prefix = "-"
            text = text[1:].strip()

        parsed = urlparse(text if "://" in text else f"https://{text}")
        domain = (parsed.netloc or parsed.path).strip().strip("/").lower()
        if not domain:
            continue

        value = f"{prefix}{domain}"
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)

    return normalized or None


def _normalize_sources(raw_sources) -> list[str]:
    if not raw_sources:
        return []

    normalized = []
    seen = set()
    for item in raw_sources:
        if isinstance(item, dict):
            candidate = item.get("url") or item.get("link") or item.get("title")
        else:
            candidate = item

        if not candidate:
            continue

        text = str(candidate).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)

    return normalized


def split_reasoning_and_answer(content: str | None, explicit_reasoning: str | None = None) -> tuple[str, str]:
    text = (content or "").strip()
    thinking_blocks = []

    if explicit_reasoning:
        explicit = str(explicit_reasoning).strip()
        if explicit:
            thinking_blocks.append(explicit)

    extracted = [match.group(1).strip() for match in THINKING_PATTERN.finditer(text)]
    thinking_blocks.extend(block for block in extracted if block)
    answer = THINKING_PATTERN.sub("", text).strip()

    thinking = "\n\n".join(block for block in thinking_blocks if block).strip()
    return thinking, answer


def append_sources_to_answer(answer: str, sources: list[str]) -> str:
    if not sources:
        return answer
    stripped_answer = answer.strip()
    sources_block = "Sources:\n" + "\n".join(sources)
    if not stripped_answer:
        return sources_block
    return stripped_answer + "\n\n" + sources_block


def call_perplexity_api(
    question: str,
    model: str = "sonar",
    whitelist: list = None,
    temperature: float = 0.9,
    max_tokens: int = 8000,
    system_prompt: str | None = None,
    api_key: str | None = None,
    search_dir: str | os.PathLike | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    **api_params,
) -> dict:
    """
    Wrapper for calling the Perplexity chat completions endpoint.

    Parameters:
      question (str): The medical question to query.
      model (str): Which model to use for the API call.
      whitelist (list): Optional list of domains for search filtering.
      api_params: Additional API parameters passed through to Perplexity.

    Returns:
      dict: A dictionary containing the answer, optional reasoning, and citations.
    """
    api_key = api_key or get_perplexity_api_key(search_dir=search_dir)
    normalized_whitelist = normalize_domain_filter(whitelist)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": model,
        "search_domain_filter": normalized_whitelist,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "system",
                "content": system_prompt or DEFAULT_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": question,
            },
        ],
    }

    payload.update({key: value for key, value in api_params.items() if value is not None})

    response = None
    try:
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        error_payload = None
        if response is not None:
            try:
                error_payload = response.json()
            except ValueError:
                error_payload = response.text
        logger.exception("Error calling Perplexity API")
        raise Exception(f"Failed to call Perplexity API: {exc}. Payload: {error_payload}") from exc

    data = response.json()
    message = {}
    if data.get("choices"):
        message = data["choices"][0].get("message", {})

    raw_content = message.get("content", "") or ""
    explicit_reasoning = message.get("reasoning") or message.get("reasoning_content")
    thinking, answer = split_reasoning_and_answer(raw_content, explicit_reasoning=explicit_reasoning)
    sources = _normalize_sources(data.get("citations") or data.get("sources") or [])

    return {
        "model": data.get("model") or model,
        "whitelist": normalized_whitelist,
        "thinking": thinking,
        "answer": answer,
        "formatted_answer": append_sources_to_answer(answer, sources),
        "sources": sources,
        "raw_content": raw_content,
    }


def run_experiment_on_question(
    question: str,
    iterations: int = 4,
    model: str = "sonar",
    temperature: float = 0.9,
    max_tokens: int = 3000,
    whitelist: list = None,
    **api_params,
) -> list:
    """
    Run the same question multiple times to collect responses for statistical variance.
    """
    results = []
    for i in range(iterations):
        max_retries = 2
        retry_count = 0
        success = False

        while retry_count <= max_retries and not success:
            try:
                result = call_perplexity_api(
                    question,
                    model=model,
                    whitelist=whitelist,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **api_params,
                )
                result["batch"] = i
                results.append(result)
                success = True
            except Exception as exc:
                retry_count += 1
                if retry_count <= max_retries:
                    logger.warning(
                        "Attempt %s failed for question '%s...' Retrying... Error: %s",
                        retry_count,
                        question[:50],
                        exc,
                    )
                else:
                    logger.error(
                        "Failed after %s retries for question '%s'. Error: %s",
                        max_retries,
                        question,
                        exc,
                    )
                    print(
                        f"SKIPPING QUESTION (after {max_retries} retries): {question}"
                    )
                    results.append(
                        {
                            "model": model,
                            "whitelist": normalize_domain_filter(whitelist),
                            "thinking": None,
                            "answer": f"ERROR: {exc}",
                            "formatted_answer": f"ERROR: {exc}",
                            "sources": [],
                            "raw_content": "",
                            "error": str(exc),
                            "batch": i,
                        }
                    )

    return results


def run_experiment_on_excel(
    input_file: str,
    output_file: str,
    iterations: int = 4,
    model: str = "sonar",
    whitelist: list = None,
    temperature: float = 0.9,
    max_tokens: int = 3000,
    **api_params,
):
    """
    Read questions from an Excel file, run experiments for each question,
    and write the results to another Excel file.
    """
    import pandas as pd

    input_df = pd.read_excel(input_file)
    results = []
    total_questions = len(input_df)

    print("Running experiment...")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print(f"Iterations: {iterations}")
    print(f"Model: {model}")
    print(f"Whitelist: {normalize_domain_filter(whitelist)}")
    print(f"Temperature: {temperature}")
    print(f"Max tokens: {max_tokens}")
    print("--------------------------------")
    print(f"Total questions to process: {total_questions}")
    print(f"Total API calls to make: {total_questions * iterations}")
    print("--------------------------------")

    progress_bar = tqdm(
        total=total_questions,
        desc="Processing questions",
        unit="question",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
    )

    for _, row in input_df.iterrows():
        question = row["Question"]
        q_short = f"{question[:30]}..." if len(question) > 30 else question
        progress_bar.set_description(f"Processing: {q_short}")

        rep_results = run_experiment_on_question(
            question,
            iterations=iterations,
            model=model,
            whitelist=whitelist,
            temperature=temperature,
            max_tokens=max_tokens,
            **api_params,
        )

        for result in rep_results:
            new_row = row.to_dict()
            new_row.update(
                {
                    "model": result.get("model", ""),
                    "whitelist": result.get("whitelist", ""),
                    "complete_answer": result.get("formatted_answer", ""),
                    "batch": result.get("batch", 0),
                }
            )
            results.append(new_row)

        progress_bar.update(1)

    progress_bar.close()

    output_df = pd.DataFrame(results)
    output_df.to_excel(output_file, index=False)
    print(f"Experiment completed. Results saved to {output_file}")


def load_dysphagia_questions(
    workbook_path: str | os.PathLike,
    sheet_name: str = "Final questions",
) -> list[dict]:
    from openpyxl import load_workbook

    workbook = load_workbook(workbook_path)
    worksheet = workbook[sheet_name]
    questions = []

    for row_idx in range(3, worksheet.max_row + 1):
        question = worksheet.cell(row=row_idx, column=DYS_PHAGIA_COLUMN_MAP["Question"]).value
        if question is None or not str(question).strip():
            continue

        questions.append(
            {
                "Category": worksheet.cell(row=row_idx, column=DYS_PHAGIA_COLUMN_MAP["Category"]).value,
                "Question number": worksheet.cell(
                    row=row_idx,
                    column=DYS_PHAGIA_COLUMN_MAP["Question number"],
                ).value,
                "Type": worksheet.cell(row=row_idx, column=DYS_PHAGIA_COLUMN_MAP["Type"]).value,
                "Question": question,
                "Sample Answer According to Guideline": worksheet.cell(
                    row=row_idx,
                    column=DYS_PHAGIA_COLUMN_MAP["Sample Answer According to Guideline"],
                ).value,
                "Guideline": worksheet.cell(row=row_idx, column=DYS_PHAGIA_COLUMN_MAP["Guideline"]).value,
            }
        )

    workbook.close()
    return questions


def is_nutrition_source_workbook(workbook_path: str | os.PathLike) -> bool:
    path = Path(workbook_path)
    if path.suffix.lower() != ".xlsx":
        return False
    if path.name.startswith("~$"):
        return False
    return not any(marker in path.stem for marker in NUTRITION_GENERATED_MARKERS)


def discover_nutrition_workbooks(
    nutrition_dir: str | os.PathLike,
) -> list[Path]:
    return sorted(
        path
        for path in Path(nutrition_dir).glob("*.xlsx")
        if is_nutrition_source_workbook(path)
    )


def _normalize_nutrition_header(value) -> str:
    header = str(value or "").strip()
    return NUTRITION_HEADER_ALIASES.get(header, header)


def _nutrition_header_map(worksheet) -> dict[str, int]:
    mapping = {}
    for column_idx in range(1, worksheet.max_column + 1):
        header = _normalize_nutrition_header(worksheet.cell(row=1, column=column_idx).value)
        if header:
            mapping[header] = column_idx
    return mapping


def load_nutrition_questions(
    workbook_path: str | os.PathLike,
    sheet_name: str | None = None,
) -> list[dict]:
    from openpyxl import load_workbook

    path = Path(workbook_path).resolve()
    workbook = load_workbook(path)
    worksheet = workbook[sheet_name or workbook.sheetnames[0]]
    header_map = _nutrition_header_map(worksheet)

    missing_fields = [
        field for field in NUTRITION_INPUT_FIELDS if field not in header_map
    ]
    if missing_fields:
        workbook.close()
        missing_text = ", ".join(missing_fields)
        raise ValueError(f"{path} is missing required Nutrition columns: {missing_text}")

    questions = []
    for row_idx in range(2, worksheet.max_row + 1):
        question = worksheet.cell(row=row_idx, column=header_map["Question"]).value
        if question is None or not str(question).strip():
            continue

        question_row = {
            "source_workbook": str(path),
            "workbook_name": path.name,
            "sheet_name": worksheet.title,
            "row_index": row_idx,
        }
        for field in NUTRITION_INPUT_FIELDS:
            question_row[field] = worksheet.cell(
                row=row_idx,
                column=header_map[field],
            ).value
        questions.append(question_row)

    workbook.close()
    return questions


def load_all_nutrition_questions(
    nutrition_dir: str | os.PathLike,
) -> list[dict]:
    questions = []
    for workbook_path in discover_nutrition_workbooks(nutrition_dir):
        questions.extend(load_nutrition_questions(workbook_path))
    return questions


def _capture_row_style(worksheet, row_idx: int, max_column: int) -> tuple[list[dict], float | None]:
    style_template = []
    for col_idx in range(1, max_column + 1):
        cell = worksheet.cell(row=row_idx, column=col_idx)
        style_template.append(
            {
                "font": copy(cell.font),
                "fill": copy(cell.fill),
                "border": copy(cell.border),
                "alignment": copy(cell.alignment),
                "number_format": cell.number_format,
                "protection": copy(cell.protection),
            }
        )
    return style_template, worksheet.row_dimensions[row_idx].height


def _apply_row_style(worksheet, row_idx: int, style_template: list[dict], row_height: float | None) -> None:
    if row_height is not None:
        worksheet.row_dimensions[row_idx].height = row_height

    for col_idx, style in enumerate(style_template, start=1):
        cell = worksheet.cell(row=row_idx, column=col_idx)
        cell.font = copy(style["font"])
        cell.fill = copy(style["fill"])
        cell.border = copy(style["border"])
        cell.alignment = copy(style["alignment"])
        cell.number_format = style["number_format"]
        cell.protection = copy(style["protection"])


def build_dysphagia_result_rows(
    workbook_path: str | os.PathLike,
    prompt_path: str | os.PathLike,
    models: list[str] | tuple[str, ...] = ("sonar", "sonar-reasoning-pro"),
    iterations: int = 1,
    whitelist: list | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4000,
    **api_params,
) -> list[dict]:
    prompt_text = load_prompt_text(prompt_path)
    questions = load_dysphagia_questions(workbook_path)
    normalized_whitelist = normalize_domain_filter(whitelist)
    results = []

    total_calls = len(questions) * len(models) * iterations
    print("Running dysphagia Perplexity export...")
    print(f"Questions: {len(questions)}")
    print(f"Models: {', '.join(models)}")
    print(f"Iterations per model: {iterations}")
    print(f"Total API calls planned: {total_calls}")
    print(f"Whitelist: {normalized_whitelist}")

    progress_bar = tqdm(
        total=total_calls,
        desc="Querying Perplexity",
        unit="call",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
    )

    for question_row in questions:
        for model in models:
            question_text = str(question_row["Question"])
            q_short = f"{question_text[:50]}..." if len(question_text) > 50 else question_text
            progress_bar.set_description(f"{model}: {q_short}")

            rep_results = run_experiment_on_question(
                question_text,
                iterations=iterations,
                model=model,
                whitelist=normalized_whitelist,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=prompt_text,
                search_dir=Path(workbook_path).parent,
                **api_params,
            )

            for result in rep_results:
                formatted_row = {
                    **question_row,
                    "model": result.get("model") or model,
                    "whitelist": ", ".join(result.get("whitelist") or []),
                    "batch": result.get("batch", 0),
                    "Thinking": result.get("thinking") or None,
                    "Answer": result.get("formatted_answer") or result.get("answer") or None,
                }
                results.append(formatted_row)

            progress_bar.update(iterations)

    progress_bar.close()
    return results


def build_nutrition_result_rows(
    nutrition_dir: str | os.PathLike,
    prompt_path: str | os.PathLike,
    models: list[str] | tuple[str, ...] = ("sonar", "sonar-reasoning-pro"),
    iterations: int = 1,
    whitelist: list | None = None,
    temperature: float = 0.2,
    max_tokens: int = 3000,
    **api_params,
) -> list[dict]:
    prompt_text = load_prompt_text(prompt_path)
    questions = load_all_nutrition_questions(nutrition_dir)
    normalized_whitelist = normalize_domain_filter(whitelist)
    results = []

    total_calls = len(questions) * len(models) * iterations
    print("Running nutrition Perplexity export...")
    print(f"Questions: {len(questions)}")
    print(f"Models: {', '.join(models)}")
    print(f"Iterations per model: {iterations}")
    print(f"Total API calls planned: {total_calls}")
    print(f"Whitelist: {normalized_whitelist}")

    progress_bar = tqdm(
        total=total_calls,
        desc="Querying Perplexity",
        unit="call",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
    )

    for question_row in questions:
        for model in models:
            question_text = str(question_row["Question"])
            q_short = f"{question_text[:50]}..." if len(question_text) > 50 else question_text
            progress_bar.set_description(f"{model}: {q_short}")

            rep_results = run_experiment_on_question(
                question_text,
                iterations=iterations,
                model=model,
                whitelist=normalized_whitelist,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=prompt_text,
                search_dir=Path(nutrition_dir),
                **api_params,
            )

            for result in rep_results:
                formatted_row = {
                    **question_row,
                    "Model": result.get("model") or model,
                    "Model Answer": (
                        result.get("formatted_answer")
                        or result.get("answer")
                        or None
                    ),
                }
                results.append(formatted_row)

            progress_bar.update(iterations)

    progress_bar.close()
    return results


def export_dysphagia_results_workbook(
    template_workbook: str | os.PathLike,
    output_workbook: str | os.PathLike,
    rows: list[dict],
    prompt_path: str | os.PathLike | None = None,
    sheet_name: str = "Final questions",
) -> str:
    from openpyxl import load_workbook

    workbook = load_workbook(template_workbook)
    worksheet = workbook[sheet_name]
    style_template, row_height = _capture_row_style(worksheet, 3, worksheet.max_column)

    if worksheet.max_row > 2:
        worksheet.delete_rows(3, worksheet.max_row - 2)

    if prompt_path and "Prompt" in workbook.sheetnames:
        workbook["Prompt"]["A2"] = load_prompt_text(prompt_path)

    ordered_fields = [
        "Category",
        "Question number",
        "Type",
        "Question",
        "Sample Answer According to Guideline",
        "Guideline",
        "model",
        "whitelist",
        "batch",
        "Thinking",
        "Answer",
    ]

    for row_offset, row_data in enumerate(rows, start=3):
        values = [row_data.get(field) for field in ordered_fields]
        values.extend([None] * (worksheet.max_column - len(values)))

        for col_idx, value in enumerate(values, start=1):
            worksheet.cell(row=row_offset, column=col_idx, value=value)

        _apply_row_style(worksheet, row_offset, style_template, row_height)

    output_path = Path(output_workbook)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    workbook.close()
    return str(output_path)


def nutrition_output_workbook_path(
    template_workbook: str | os.PathLike,
    suffix: str,
    output_dir: str | os.PathLike | None = None,
) -> Path:
    template = Path(template_workbook)
    normalized_suffix = suffix if suffix.startswith("_") else f"_{suffix}"
    if normalized_suffix.endswith(".xlsx"):
        output_name = f"{template.stem}{normalized_suffix}"
    else:
        output_name = f"{template.stem}{normalized_suffix}.xlsx"

    return Path(output_dir) / output_name if output_dir else template.with_name(output_name)


def export_nutrition_results_workbook(
    template_workbook: str | os.PathLike,
    output_workbook: str | os.PathLike,
    rows: list[dict],
    sheet_name: str | None = None,
) -> str:
    from openpyxl import load_workbook

    workbook = load_workbook(template_workbook)
    worksheet = workbook[sheet_name or workbook.sheetnames[0]]
    style_template, row_height = _capture_row_style(worksheet, 2, worksheet.max_column)

    if worksheet.max_row > 1:
        worksheet.delete_rows(2, worksheet.max_row - 1)

    ordered_fields = NUTRITION_INPUT_FIELDS + NUTRITION_RESULT_FIELDS

    for row_offset, row_data in enumerate(rows, start=2):
        values = [row_data.get(field) for field in ordered_fields]
        values.extend([None] * (worksheet.max_column - len(values)))

        for col_idx, value in enumerate(values, start=1):
            worksheet.cell(row=row_offset, column=col_idx, value=value)

        _apply_row_style(worksheet, row_offset, style_template, row_height)

    output_path = Path(output_workbook)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    workbook.close()
    return str(output_path)


def export_nutrition_results_workbooks(
    rows: list[dict],
    suffix: str,
    output_dir: str | os.PathLike | None = None,
) -> dict[str, str]:
    grouped_rows: dict[Path, list[dict]] = {}
    for row in rows:
        source_workbook = Path(row["source_workbook"]).resolve()
        grouped_rows.setdefault(source_workbook, []).append(row)

    exported_paths = {}
    for source_workbook, workbook_rows in sorted(grouped_rows.items()):
        output_workbook = nutrition_output_workbook_path(
            source_workbook,
            suffix=suffix,
            output_dir=output_dir,
        )
        sheet_name = workbook_rows[0].get("sheet_name")
        exported_paths[str(source_workbook)] = export_nutrition_results_workbook(
            template_workbook=source_workbook,
            output_workbook=output_workbook,
            rows=workbook_rows,
            sheet_name=sheet_name,
        )
    return exported_paths


def run_dysphagia_export(
    template_workbook: str | os.PathLike,
    output_workbook: str | os.PathLike,
    prompt_path: str | os.PathLike,
    models: list[str] | tuple[str, ...] = ("sonar", "sonar-reasoning-pro"),
    iterations: int = 1,
    whitelist: list | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4000,
    **api_params,
) -> str:
    rows = build_dysphagia_result_rows(
        workbook_path=template_workbook,
        prompt_path=prompt_path,
        models=models,
        iterations=iterations,
        whitelist=whitelist,
        temperature=temperature,
        max_tokens=max_tokens,
        **api_params,
    )
    return export_dysphagia_results_workbook(
        template_workbook=template_workbook,
        output_workbook=output_workbook,
        rows=rows,
        prompt_path=prompt_path,
    )


def run_nutrition_export(
    nutrition_dir: str | os.PathLike,
    prompt_path: str | os.PathLike,
    output_dir: str | os.PathLike | None = None,
    output_suffix: str = "_perplexity_sonar_reasoning",
    models: list[str] | tuple[str, ...] = ("sonar", "sonar-reasoning-pro"),
    iterations: int = 1,
    whitelist: list | None = None,
    temperature: float = 0.2,
    max_tokens: int = 3000,
    **api_params,
) -> dict[str, str]:
    rows = build_nutrition_result_rows(
        nutrition_dir=nutrition_dir,
        prompt_path=prompt_path,
        models=models,
        iterations=iterations,
        whitelist=whitelist,
        temperature=temperature,
        max_tokens=max_tokens,
        **api_params,
    )
    return export_nutrition_results_workbooks(
        rows=rows,
        suffix=output_suffix,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    print("Running experiment...")
    print("Input file: questions.xlsx")
    print("Output file: results.xlsx")
    print("Iterations: 4")
    print("Model: sonar")
    print("Whitelist: https://www.aan.com")
    print("Temperature: 0.9")
    print("Max tokens: 3000")
    run_experiment_on_excel(
        input_file="questions.xlsx",
        output_file="results.xlsx",
        iterations=4,
        model="sonar",
        whitelist=["https://www.aan.com"],
        temperature=0.9,
        max_tokens=8000,
    )
