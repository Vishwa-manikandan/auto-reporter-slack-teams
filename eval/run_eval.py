"""Evaluate an extractor against the hand-labelled set.

Usage:
    python eval/run_eval.py             # rules baseline + thresholds
    python eval/run_eval.py --json      # also write eval/results.json

The runner makes no network calls by default, so CI and local runs produce
identical numbers. It exits non-zero when precision, recall or owner accuracy
falls below the configured floors, which is what makes the CI job meaningful.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.rule_extractor import CATEGORIES, RuleExtractor  # noqa: E402

EVAL_SET = Path(__file__).with_name("eval_set.json")
RESULTS = Path(__file__).with_name("results.json")


def load_cases() -> List[Dict[str, Any]]:
    with EVAL_SET.open(encoding="utf-8") as handle:
        return json.load(handle)["cases"]


def evaluate(cases: List[Dict[str, Any]], extractor: Optional[Any] = None) -> Dict[str, Any]:
    extractor = extractor or RuleExtractor()
    stats = {category: {"tp": 0, "fp": 0, "fn": 0} for category in CATEGORIES}
    owners_expected = 0
    owners_correct = 0
    exact_cases = 0
    failures: List[Dict[str, Any]] = []

    for case in cases:
        messages = case["messages"]
        predicted: Dict[str, set[int]] = {category: set() for category in CATEGORIES}
        predicted_by_index: Dict[tuple[int, str], Dict[str, Any]] = {}
        for item in extractor.extract(messages):
            predicted[item.category].add(item.msg_index)
            predicted_by_index[(item.msg_index, item.category)] = item.as_dict()

        expected: Dict[str, set[int]] = {}
        for category in CATEGORIES:
            expected[category] = set(case.get("expected", {}).get(category, []))

        case_failures = []
        for category in CATEGORIES:
            tp = len(predicted[category] & expected[category])
            fp = len(predicted[category] - expected[category])
            fn = len(expected[category] - predicted[category])
            stats[category]["tp"] += tp
            stats[category]["fp"] += fp
            stats[category]["fn"] += fn
            if fp or fn:
                case_failures.append(
                    {
                        "category": category,
                        "false_positives": sorted(predicted[category] - expected[category]),
                        "false_negatives": sorted(expected[category] - predicted[category]),
                    }
                )

        case_owners_expected = case.get("expected_owners", {})
        for index_text, owner in case_owners_expected.items():
            owners_expected += 1
            item = predicted_by_index.get((int(index_text), "action_item"))
            if item and item.get("owner") == owner.lower():
                owners_correct += 1
            else:
                case_failures.append(
                    {
                        "category": "owner",
                        "message_index": int(index_text),
                        "expected": owner,
                        "predicted": item.get("owner") if item else None,
                    }
                )

        if not case_failures:
            exact_cases += 1
        else:
            failures.append({"case": case["id"], "issues": case_failures})

    totals = {"tp": 0, "fp": 0, "fn": 0}
    per_category = {}
    for category, values in stats.items():
        totals["tp"] += values["tp"]
        totals["fp"] += values["fp"]
        totals["fn"] += values["fn"]
        per_category[category] = _with_scores(values)

    return {
        "cases": len(cases),
        "exact_match_cases": exact_cases,
        "per_category": per_category,
        "micro": _with_scores(totals),
        "owners": {
            "expected": owners_expected,
            "correct": owners_correct,
            "accuracy": round(owners_correct / owners_expected, 3) if owners_expected else None,
        },
        "failures": failures,
    }


def _with_scores(values: Dict[str, int]) -> Dict[str, Any]:
    tp, fp, fn = values["tp"], values["fp"], values["fn"]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    if precision is None or recall is None or precision + recall == 0:
        f1 = None
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 3) if precision is not None else None,
        "recall": round(recall, 3) if recall is not None else None,
        "f1": round(f1, 3) if f1 is not None else None,
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def print_report(result: Dict[str, Any]) -> None:
    print(f"Cases: {result['cases']}  Exact thread matches: {result['exact_match_cases']}")
    print()
    print("| Category | TP | FP | FN | Precision | Recall | F1 |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for category, scores in result["per_category"].items():
        print(
            f"| {category} | {scores['tp']} | {scores['fp']} | {scores['fn']} "
            f"| {_fmt(scores['precision'])} | {_fmt(scores['recall'])} | {_fmt(scores['f1'])} |"
        )
    micro = result["micro"]
    print(
        f"| **micro** | {micro['tp']} | {micro['fp']} | {micro['fn']} "
        f"| **{_fmt(micro['precision'])}** | **{_fmt(micro['recall'])}** | **{_fmt(micro['f1'])}** |"
    )
    owners = result["owners"]
    print()
    print(f"Owner accuracy: {owners['correct']}/{owners['expected']} ({_fmt(owners['accuracy'])})")
    if result["failures"]:
        print()
        print("Mismatches:")
        for failure in result["failures"]:
            print(f"  - {failure['case']}: {json.dumps(failure['issues'], sort_keys=True)}")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the extraction evaluation set")
    parser.add_argument("--json", action="store_true", help="write eval/results.json")
    parser.add_argument("--min-precision", type=float, default=0.85)
    parser.add_argument("--min-recall", type=float, default=0.60)
    parser.add_argument("--min-owner-accuracy", type=float, default=0.80)
    args = parser.parse_args(argv)

    result = evaluate(load_cases())
    print_report(result)

    if args.json:
        RESULTS.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {RESULTS.relative_to(ROOT)}")

    micro = result["micro"]
    failures = []
    if micro["precision"] is None or micro["precision"] < args.min_precision:
        failures.append(f"precision {_fmt(micro['precision'])} < {args.min_precision}")
    if micro["recall"] is None or micro["recall"] < args.min_recall:
        failures.append(f"recall {_fmt(micro['recall'])} < {args.min_recall}")
    owner_accuracy = result["owners"]["accuracy"]
    if owner_accuracy is None or owner_accuracy < args.min_owner_accuracy:
        failures.append(f"owner accuracy {_fmt(owner_accuracy)} < {args.min_owner_accuracy}")

    if failures:
        print("\nTHRESHOLD FAILED: " + "; ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
