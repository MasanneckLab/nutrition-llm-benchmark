#!/usr/bin/env python3
"""Independent reconstruction of the central Nutrition benchmark results.

This script deliberately does not import functions from ``analysis/``. It checks
the three deposited core tables against one another, rebuilds topic pairs, and
uses exact permutation distributions where their size is manageable.
"""

from __future__ import annotations

import csv
import itertools
import json
import math
import random
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MODELS = ("Open Evidence", "GPT-5.5", "Sonar Reasoning Pro")
DOMAINS = ("Domain 1", "Domain 2", "Domain 3")
ORDINAL = {"No": 0, "Partly": 1, "Yes": 2}


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def short_question_id(value: str) -> str:
    return value.split("|", 1)[-1]


def holm(p_values: list[Fraction]) -> list[Fraction]:
    order = sorted(range(len(p_values)), key=p_values.__getitem__)
    adjusted = [Fraction(0)] * len(p_values)
    running = Fraction(0)
    for rank, index in enumerate(order):
        running = max(running, p_values[index] * (len(p_values) - rank))
        adjusted[index] = min(Fraction(1), running)
    return adjusted


def exact_sign_flip_p(differences: list[Fraction]) -> Fraction:
    """Two-sided paired sign-flip test by dynamic programming."""
    nonzero = [value for value in differences if value]
    distribution: Counter[Fraction] = Counter({Fraction(0): 1})
    for value in nonzero:
        updated: Counter[Fraction] = Counter()
        for total, count in distribution.items():
            updated[total + value] += count
            updated[total - value] += count
        distribution = updated

    observed = abs(sum(differences, Fraction(0)))
    hits = sum(count for total, count in distribution.items() if abs(total) >= observed)
    return Fraction(hits, 2 ** len(nonzero))


def exact_within_topic_omnibus_p(matrix: list[list[Fraction]]) -> Fraction:
    """Permute three system labels within each topic and enumerate the distribution."""
    column_totals = [
        sum((row[column] for row in matrix), Fraction(0)) for column in range(3)
    ]
    grand_total = sum(column_totals, Fraction(0))
    grand_column = grand_total / 3
    observed = sum((value - grand_column) ** 2 for value in column_totals)

    distribution: Counter[tuple[Fraction, Fraction]] = Counter(
        {(Fraction(0), Fraction(0)): 1}
    )
    running_total = Fraction(0)
    for row in matrix:
        running_total += sum(row, Fraction(0))
        row_permutations = Counter(itertools.permutations(row))
        updated: Counter[tuple[Fraction, Fraction]] = Counter()
        for (first, second), count in distribution.items():
            for permutation, permutation_count in row_permutations.items():
                updated[(first + permutation[0], second + permutation[1])] += (
                    count * permutation_count
                )
        distribution = updated

    hits = 0
    for (first, second), count in distribution.items():
        third = running_total - first - second
        expected = running_total / 3
        statistic = (first - expected) ** 2 + (second - expected) ** 2 + (third - expected) ** 2
        if statistic >= observed:
            hits += count
    return Fraction(hits, 6 ** len(matrix))


def exact_grade_p(
    model: str,
    topics: list[tuple[str, str]],
    grade: dict[tuple[str, str], str],
    topic_values: dict[tuple[str, tuple[str, str]], Fraction],
) -> Fraction:
    """Enumerate grade assignments within each domain, preserving group sizes."""

    def contribution(domain: str, graded_positions: frozenset[int]) -> Fraction:
        domain_topics = [topic for topic in topics if topic[0] == domain]
        graded = [
            topic_values[(model, topic)]
            for index, topic in enumerate(domain_topics)
            if index in graded_positions
        ]
        gpp = [
            topic_values[(model, topic)]
            for index, topic in enumerate(domain_topics)
            if index not in graded_positions
        ]
        return (
            sum(graded, Fraction(0)) / len(graded)
            - sum(gpp, Fraction(0)) / len(gpp)
        )

    observed = Fraction(0)
    domain_distributions: list[Counter[Fraction]] = []
    total_assignments = 1
    for domain in DOMAINS:
        domain_topics = [topic for topic in topics if topic[0] == domain]
        actual = frozenset(
            index
            for index, topic in enumerate(domain_topics)
            if grade[topic] == "graded"
        )
        observed += contribution(domain, actual)
        assignments = Counter(
            contribution(domain, frozenset(chosen))
            for chosen in itertools.combinations(range(len(domain_topics)), len(actual))
        )
        domain_distributions.append(assignments)
        total_assignments *= sum(assignments.values())

    distribution: Counter[Fraction] = Counter({Fraction(0): 1})
    for domain_distribution in domain_distributions:
        updated: Counter[Fraction] = Counter()
        for left, left_count in distribution.items():
            for right, right_count in domain_distribution.items():
                updated[left + right] += left_count * right_count
        distribution = updated

    hits = sum(
        count for value, count in distribution.items() if abs(value) >= abs(observed)
    )
    return Fraction(hits, total_assignments)


def pseudo_f(values: list[float], labels: list[str]) -> float:
    grand_mean = sum(values) / len(values)
    grouped = {
        domain: [value for value, label in zip(values, labels) if label == domain]
        for domain in DOMAINS
    }
    between = sum(
        len(group) * (sum(group) / len(group) - grand_mean) ** 2
        for group in grouped.values()
    )
    within = sum(
        sum((value - sum(group) / len(group)) ** 2 for value in group)
        for group in grouped.values()
    )
    return (between / 2) / (within / (len(values) - 3))


def topic_domain_permutation_p(
    values: list[float], labels: list[str], seed: int, permutations: int = 200_000
) -> tuple[float, float]:
    """Monte Carlo omnibus test over 30 topic means, with balanced domains."""
    sizes = [labels.count(domain) for domain in DOMAINS]
    require(sizes == [10, 10, 10], f"Unexpected domain sizes: {sizes}")
    observed_f = pseudo_f(values, labels)

    grand_mean = sum(values) / len(values)
    observed_between = sum(
        sizes[index]
        * (
            sum(value for value, label in zip(values, labels) if label == domain)
            / sizes[index]
            - grand_mean
        )
        ** 2
        for index, domain in enumerate(DOMAINS)
    )

    shuffled = list(values)
    rng = random.Random(seed)
    hits = 0
    for _ in range(permutations):
        rng.shuffle(shuffled)
        starts = (0, sizes[0], sizes[0] + sizes[1])
        between = 0.0
        for start, size in zip(starts, sizes):
            group_mean = sum(shuffled[start : start + size]) / size
            between += size * (group_mean - grand_mean) ** 2
        if between >= observed_between - 1e-12:
            hits += 1
    return observed_f, (hits + 1) / (permutations + 1)


def exact_two_group_p(left: list[Fraction], right: list[Fraction]) -> Fraction:
    """Two-sided randomization test for two groups of ten topic means."""
    require(len(left) == len(right) == 10, "Domain pair must contain 10 topics each")
    values = left + right
    group_size = len(left)
    total_sum = sum(values, Fraction(0))
    observed = abs(sum(left, Fraction(0)) / group_size - sum(right, Fraction(0)) / group_size)
    hits = 0
    total = 0
    for chosen in itertools.combinations(range(len(values)), group_size):
        chosen_sum = sum((values[index] for index in chosen), Fraction(0))
        difference = abs(
            chosen_sum / group_size
            - (total_sum - chosen_sum) / (len(values) - group_size)
        )
        hits += difference >= observed
        total += 1
    return Fraction(hits, total)


def main() -> None:
    answers = read_csv("answers_v2.csv")
    raters = read_csv("ratings_raters.csv")
    items = read_csv("items_master.csv")

    answer_key = {
        (row["model"], row["domain"], row["question_id"]): row for row in answers
    }
    rater_key = {
        (row["model"], row["domain"], short_question_id(row["question_id"])): row
        for row in raters
    }
    item_key = {row["question_id"]: row for row in items}

    require(len(answers) == len(answer_key) == 180, "answers_v2 must have 180 unique rows")
    require(len(raters) == 180, "ratings_raters must have 180 rows")
    require(len({row["rating_id"] for row in raters}) == 180, "Rating IDs are not unique")
    require(len(items) == len(item_key) == 60, "items_master must have 60 unique rows")
    require(set(answer_key) == set(rater_key), "Answer and rater keys differ")

    model_counts = Counter(row["model"] for row in answers)
    require(model_counts == Counter({model: 60 for model in MODELS}), "Model counts differ")
    item_required = [column for column in items[0] if column != "sign_grade_note"]
    require(
        not any(not row[column] for row in items for column in item_required),
        "items_master contains a blank required field",
    )

    consensus_columns = {
        "glr": "guideline_reference",
        "accuracy": "accuracy",
        "safety": "safety_concern",
        "evidence": "evidence_level",
    }
    for answer_column, rater_column in consensus_columns.items():
        require(
            all(
                row[answer_column]
                == rater_key[(row["model"], row["domain"], row["question_id"])][
                    "consensus_" + rater_column
                ]
                for row in answers
            ),
            f"Consensus mismatch for {answer_column}",
        )

    item_prefix = {
        "Open Evidence": "oe",
        "GPT-5.5": "gpt",
        "Sonar Reasoning Pro": "sonar",
    }
    for row in answers:
        item = item_key[f"{row['domain']}|{row['question_id']}"]
        prefix = item_prefix[row["model"]]
        require(row["accuracy"] == item[f"{prefix}_accuracy"], "Item accuracy mismatch")
        require(
            row["glr"] == item[f"{prefix}_guideline_reference"],
            "Item reference mismatch",
        )
        require(row["safety"] == item[f"{prefix}_safety_concern"], "Item safety mismatch")

    by_topic: dict[tuple[str, tuple[str, str]], list[dict[str, str]]] = defaultdict(list)
    for row in answers:
        topic = (row["domain"], row["question_id"][:-1])
        by_topic[(row["model"], topic)].append(row)
    topics = sorted(
        {topic for _, topic in by_topic}, key=lambda value: (value[0], int(value[1]))
    )
    require(len(topics) == 30, "Expected 30 topics")
    require(
        all(len(by_topic[(model, topic)]) == 2 for model in MODELS for topic in topics),
        "Every model-topic cell must contain two questions",
    )

    def topic_mean(model: str, topic: tuple[str, str], endpoint: str) -> Fraction:
        rows = by_topic[(model, topic)]
        if endpoint == "exact":
            values = [int(row["glr"] == "Yes") for row in rows]
        elif endpoint == "ordinal":
            values = [ORDINAL[row["glr"]] for row in rows]
        elif endpoint == "evidence":
            values = [int(row["evidence"] == "Yes") for row in rows]
        elif endpoint == "safety":
            values = [int(row["safety"] != "No") for row in rows]
        else:
            values = [int(row["accuracy"] == "Correct") for row in rows]
        return Fraction(sum(values), len(values))

    print("DATA INTEGRITY")
    print("  60 questions, 30 topics, 180 answer rows: OK")
    print("  answers, raters and item master reconcile: OK")

    correct = {
        model: sum(row["accuracy"] == "Correct" for row in answers if row["model"] == model)
        for model in MODELS
    }
    exact = {
        model: sum(row["glr"] == "Yes" for row in answers if row["model"] == model)
        for model in MODELS
    }
    require(tuple(correct.values()) == (54, 54, 47), "Correct-answer counts changed")
    require(tuple(exact.values()) == (21, 41, 31), "Exact-reference counts changed")

    print("\nCENTRAL COUNTS")
    for model in MODELS:
        print(f"  {model:<22} correct {correct[model]:2d}/60   exact reference {exact[model]:2d}/60")

    agreement_order = (
        "accuracy",
        "guideline_reference",
        "evidence_level",
        "safety_concern",
    )
    agreement = {
        column: 100
        * sum(row[f"rater_1_{column}"] == row[f"rater_2_{column}"] for row in raters)
        / len(raters)
        for column in agreement_order
    }
    expected_agreement = (92.2222222222, 88.8888888889, 88.3333333333, 95.0)
    require(
        all(math.isclose(value, expected, abs_tol=1e-9) for value, expected in zip(agreement.values(), expected_agreement)),
        "Agreement percentages changed",
    )
    print("\nEXACT RATER AGREEMENT")
    for column in agreement_order:
        print(f"  {column:<23} {agreement[column]:5.1f}%")

    print("\nTOPIC-LEVEL SENSITIVITY FOR OTHER ENDPOINTS")
    for endpoint in ("accuracy", "evidence", "safety"):
        matrix = [
            [topic_mean(model, topic, endpoint) for model in MODELS]
            for topic in topics
        ]
        omnibus_p = exact_within_topic_omnibus_p(matrix)
        pairwise_p = []
        for left, right in (
            ("Open Evidence", "GPT-5.5"),
            ("Open Evidence", "Sonar Reasoning Pro"),
            ("GPT-5.5", "Sonar Reasoning Pro"),
        ):
            pairwise_p.append(
                exact_sign_flip_p(
                    [
                        topic_mean(left, topic, endpoint)
                        - topic_mean(right, topic, endpoint)
                        for topic in topics
                    ]
                )
            )
        adjusted = holm(pairwise_p)
        print(
            f"  {endpoint:<9} exact omnibus p={float(omnibus_p):.6f}; "
            f"pairwise Holm p="
            + ", ".join(f"{float(value):.6f}" for value in adjusted)
        )

    contrast_names = (
        ("Open Evidence", "GPT-5.5"),
        ("Open Evidence", "Sonar Reasoning Pro"),
        ("GPT-5.5", "Sonar Reasoning Pro"),
    )
    contrast_p = []
    contrast_effect = []
    for left, right in contrast_names:
        differences = [topic_mean(left, topic, "exact") - topic_mean(right, topic, "exact") for topic in topics]
        contrast_effect.append(sum(differences, Fraction(0)) / len(differences))
        contrast_p.append(exact_sign_flip_p(differences))
    contrast_holm = holm(contrast_p)
    gpt_minus_open = -contrast_effect[0]
    require(gpt_minus_open == Fraction(1, 3), "GPT-5.5 effect changed")
    require(contrast_holm[0] < Fraction(1, 20), "GPT-5.5 contrast is no longer below 0.05")

    print("\nEXACT TOPIC-LEVEL SIGN-FLIP TEST, EXACT REFERENCE")
    for (left, right), effect, raw_p, adjusted_p in zip(
        contrast_names, contrast_effect, contrast_p, contrast_holm
    ):
        print(
            f"  {left} vs {right}: {100 * float(effect):+.1f} pp, "
            f"raw p={float(raw_p):.6f}, Holm p={float(adjusted_p):.6f}"
        )
    print("  Reported Monte Carlo value for GPT-5.5 vs Open Evidence: Holm p=0.0381")

    grade: dict[tuple[str, str], str] = {}
    for item in items:
        domain, question_id = item["question_id"].split("|", 1)
        topic = (domain, question_id[:-1])
        label = "GPP" if item["sign_grade"] == "GPP" else "graded"
        require(topic not in grade or grade[topic] == label, f"Grade differs within {topic}")
        grade[topic] = label
    require(Counter(grade.values()) == Counter({"graded": 12, "GPP": 18}), "Grade counts changed")

    ordinal_topic_values = {
        (model, topic): topic_mean(model, topic, "ordinal")
        for model in MODELS
        for topic in topics
    }
    grade_p = [exact_grade_p(model, topics, grade, ordinal_topic_values) for model in MODELS]
    grade_holm = holm(grade_p)
    open_rows = [row for row in answers if row["model"] == "Open Evidence"]
    open_yes = {
        label: sum(
            row["glr"] == "Yes"
            for row in open_rows
            if grade[(row["domain"], row["question_id"][:-1])] == label
        )
        for label in ("graded", "GPP")
    }
    require(open_yes == {"graded": 1, "GPP": 20}, "Open Evidence grade counts changed")
    require(grade_holm[0] < Fraction(1, 200), "Open Evidence grade result changed")

    print("\nGRADE OF RECOMMENDATION, ORDINAL TOPIC MEANS")
    for model, raw_p, adjusted_p in zip(MODELS, grade_p, grade_holm):
        graded_values = [ordinal_topic_values[(model, topic)] for topic in topics if grade[topic] == "graded"]
        gpp_values = [ordinal_topic_values[(model, topic)] for topic in topics if grade[topic] == "GPP"]
        print(
            f"  {model:<22} graded {float(sum(graded_values, Fraction(0)) / len(graded_values)):.3f}, "
            f"GPP {float(sum(gpp_values, Fraction(0)) / len(gpp_values)):.3f}, "
            f"exact raw p={float(raw_p):.6f}, Holm p={float(adjusted_p):.6f}"
        )
    print("  Open Evidence exact-reference counts: 1/24 graded vs 20/36 GPP")
    print("  Reported Monte Carlo value for Open Evidence: Holm p=0.0045")

    replacement_metadata = json.loads(
        (ROOT / "querying" / "replacement_queries.json").read_text(encoding="utf-8")
    )
    replacement_ids = set(replacement_metadata["rating_ids"])
    truncated_ids = {
        row["rating_id"] for row in read_csv("truncated_responses.csv")
    }
    sonar_ratings = [row for row in raters if row["model"] == "Sonar Reasoning Pro"]
    replacement_rows = [row for row in sonar_ratings if row["rating_id"] in replacement_ids]
    retained_rows = [row for row in sonar_ratings if row["rating_id"] not in replacement_ids]
    require(len(replacement_ids) == len(replacement_rows) == 13, "Replacement ID set changed")
    require(not replacement_ids & truncated_ids, "A replacement answer is marked truncated")
    require(len(truncated_ids) == 22, "Expected 22 truncated Sonar responses")
    require(
        all(row["model"] == "Sonar Reasoning Pro" for row in read_csv("truncated_responses.csv")),
        "A non-Sonar response is marked truncated",
    )

    print("\nSONAR ACQUISITION SENSITIVITY")
    for label, rows_subset in (
        ("replacement", replacement_rows),
        ("initial retained", retained_rows),
    ):
        correct_count = sum(row["consensus_accuracy"] == "Correct" for row in rows_subset)
        reference_count = sum(
            row["consensus_guideline_reference"] == "Yes" for row in rows_subset
        )
        print(
            f"  {label:<16} n={len(rows_subset):2d}, correct {correct_count:2d}, "
            f"exact reference {reference_count:2d}"
        )
    print("  truncated answers: 22 initial-run Sonar responses, 0 replacements")

    topic_domain_values: dict[str, list[Fraction]] = {}
    topic_labels = [topic[0] for topic in topics]
    for endpoint in ("exact", "ordinal"):
        topic_domain_values[endpoint] = [
            sum((topic_mean(model, topic, endpoint) for model in MODELS), Fraction(0))
            / len(MODELS)
            for topic in topics
        ]
    domain_tests = [
        topic_domain_permutation_p(
            [float(value) for value in topic_domain_values[endpoint]],
            topic_labels,
            seed=20260914 + index,
        )
        for index, endpoint in enumerate(("exact", "ordinal"))
    ]
    domain_raw = [Fraction(round(p_value * 1_000_000), 1_000_000) for _, p_value in domain_tests]
    domain_holm = holm(domain_raw)

    pair_names = list(itertools.combinations(DOMAINS, 2))
    pair_p = []
    pair_effect = []
    for left, right in pair_names:
        left_values = [value for value, topic in zip(topic_domain_values["exact"], topics) if topic[0] == left]
        right_values = [value for value, topic in zip(topic_domain_values["exact"], topics) if topic[0] == right]
        pair_effect.append(sum(left_values, Fraction(0)) / 10 - sum(right_values, Fraction(0)) / 10)
        pair_p.append(exact_two_group_p(left_values, right_values))
    pair_holm = holm(pair_p)

    print("\nTOPIC-LEVEL DOMAIN SENSITIVITY")
    for endpoint, (statistic, p_value), adjusted_p in zip(
        ("exact", "ordinal"), domain_tests, domain_holm
    ):
        print(
            f"  {endpoint:<8} pseudo-F={statistic:.4f}, Monte Carlo p={p_value:.4f}, "
            f"Holm p={float(adjusted_p):.4f}"
        )
    for (left, right), effect, raw_p, adjusted_p in zip(
        pair_names, pair_effect, pair_p, pair_holm
    ):
        print(
            f"  {left} vs {right}: {100 * float(effect):+.1f} pp, "
            f"exact p={float(raw_p):.4f}, Holm p={float(adjusted_p):.4f}"
        )

    print("\nALL INDEPENDENT CHECKS PASSED")


if __name__ == "__main__":
    main()
