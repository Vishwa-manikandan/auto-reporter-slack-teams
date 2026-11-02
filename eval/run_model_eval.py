"""Evaluate a live model on the same labelled set as the rules baseline.

This is intentionally opt-in: CI has no model credentials, so the rules
baseline is the gate. Run this locally to fill the model row of the comparison
table.

Usage:
    python eval/run_model_eval.py --provider ollama --model llama3.2:latest --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.demo import AI_PROMPT, _ai_items, _parse_json  # noqa: E402
from app.services.ai_provider import AIProviderFactory  # noqa: E402
from app.services.rule_extractor import ExtractedItem  # noqa: E402
from eval.run_eval import evaluate, load_cases, print_report  # noqa: E402

MODEL_RESULTS = Path(__file__).with_name("model_results.json")


class ModelExtractor:
    """Adapt the async AI provider to the synchronous extractor interface."""

    def __init__(self, provider_name: str, model: Optional[str] = None):
        self.provider_name = provider_name
        self.provider = AIProviderFactory.create(provider_name)
        if model:
            self.provider.model = model
        self.model = getattr(self.provider, "model", model)

    def extract(self, messages: List[Dict[str, Any]]) -> List[ExtractedItem]:
        payload = [
            {"index": index, "user": message.get("user") or "", "text": message.get("text") or ""}
            for index, message in enumerate(messages)
        ]
        raw = asyncio.run(self.provider.generate(payload, AI_PROMPT))
        try:
            data = _parse_json(raw)
        except Exception:
            return []

        extracted: List[ExtractedItem] = []
        for item in _ai_items(data, messages):
            index = item["msg_index"] if item["msg_index"] is not None else -1
            extracted.append(
                ExtractedItem(
                    category=item["category"],
                    text=item["text"],
                    msg_index=index,
                    speaker=item.get("speaker"),
                    owner=item.get("owner"),
                    confidence=float(item.get("confidence") or 0.8),
                    cues=["ai"],
                )
            )
        return extracted


class Progress:
    def __init__(self, inner: ModelExtractor, cases: List[Dict[str, Any]]):
        self.inner = inner
        self.cases = cases
        self.index = 0

    def extract(self, messages: List[Dict[str, Any]]) -> List[ExtractedItem]:
        case_id = self.cases[self.index]["id"]
        self.index += 1
        print(f"[{self.index}/{len(self.cases)}] {case_id}", file=sys.stderr)
        return self.inner.extract(messages)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate a live model on the labelled set")
    parser.add_argument("--provider", default="ollama", help="mock, anthropic, ollama or openai")
    parser.add_argument("--model", default="llama3.2:latest")
    parser.add_argument("--json", action="store_true", help="write eval/model_results.json")
    args = parser.parse_args(argv)

    cases = load_cases()
    extractor = ModelExtractor(args.provider, args.model)
    print(f"Provider: {args.provider}  model: {extractor.model}", file=sys.stderr)

    result = evaluate(cases, extractor=Progress(extractor, cases))
    result["method"] = {"provider": args.provider, "model": extractor.model}
    print_report(result)

    if args.json:
        MODEL_RESULTS.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {MODEL_RESULTS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
