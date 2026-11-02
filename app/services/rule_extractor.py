"""Deterministic, dependency-free extraction of report items from Slack messages.

This is the reproducible baseline used by the evaluation harness and by the UI
when no AI provider is configured. It is intentionally conservative: precision
matters more than recall, because a report that invents blockers is worse than
one that misses a few.

Two classes of false positive are handled explicitly:

* negation - "the deploy is not blocked anymore" must not produce a blocker.
* quoted text - blockquotes, inline code and attributed quotes ("Alice said:
  ...") describe someone else's words and are not classified.

Every emitted item carries a confidence score so the UI can show how strong the
signal was instead of presenting all matches as equally certain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

CATEGORIES = ("blocker", "action_item", "decision", "bug", "feature_request")

# (pattern, confidence). Strong cues are explicit statements; weak cues are
# suggestive phrasing that needs the surrounding sentence to carry it.
_CUES: Dict[str, List[tuple[str, float]]] = {
    "blocker": [
        (r"\bblocked\b", 0.92),
        (r"\bblocker\b", 0.90),
        (r"\bblocking\b", 0.85),
        (r"\bstuck\b", 0.85),
        (r"\bwaiting (?:on|for)\b", 0.85),
        (r"\bcan(?:'|no)t proceed\b", 0.90),
        (r"\bheld up\b", 0.80),
        (r"\bon hold\b", 0.75),
        (r"\bunreachable\b", 0.90),
        (r"\boutage\b", 0.88),
        (r"\bdepends on\b", 0.62),
    ],
    "action_item": [
        (r"\baction item\b", 0.92),
        (r"\bto-?do\b", 0.85),
        (r"\bassigned to\b", 0.88),
        (r"\bneeds? to\b", 0.78),
        (r"\bneed to\b", 0.78),
        (r"\bcan someone\b", 0.80),
        (r"\bplease\b", 0.70),
        (r"\bfollow up\b", 0.80),
        (r"\bi'?ll\b", 0.75),
        (r"\bi will\b", 0.75),
        (r"\b(?!(?:We|It|They|This|That|There|He|She|You|I)\b)[A-Z][a-z]+ will\b", 0.72),
    ],
    "decision": [
        (r"\bdecided\b", 0.92),
        (r"\bdecision\b", 0.88),
        (r"\bwe agreed\b", 0.88),
        (r"\bagreed to\b", 0.85),
        (r"\bgoing with\b", 0.82),
        (r"\bwe will not\b", 0.85),
        (r"\bwe will ship\b", 0.80),
        (r"\bfinal call\b", 0.80),
        (r"\bsettled on\b", 0.78),
        (r"\bapproved\b", 0.72),
    ],
    "bug": [
        (r"\bbug\b", 0.90),
        (r"\bregression\b", 0.90),
        (r"\bcrash(?:es|ed|ing)?\b", 0.88),
        (r"\bexception\b", 0.82),
        (r"\b500\b", 0.85),
        (r"\berrors?\b", 0.78),
        (r"\bmemory leak\b", 0.90),
        (r"\bbroken\b", 0.80),
        (r"\bfail(?:s|ed|ing)?\b", 0.72),
        (r"\bflaky\b", 0.72),
    ],
    "feature_request": [
        (r"\bfeature request\b", 0.92),
        (r"\bcould we add\b", 0.85),
        (r"\bcan we add\b", 0.82),
        (r"\bwould be nice\b", 0.78),
        (r"\bnice to have\b", 0.78),
        (r"\badd support for\b", 0.82),
        (r"\bsupport for\b", 0.70),
    ],
}

# Words that invert the cue in the same clause.
_NEGATION_RE = re.compile(
    r"\b(?:not|no|never|none|without|isn't|aren't|wasn't|weren't|don't|doesn't|"
    r"didn't|can't|cannot|won't|no longer)\b",
    re.I,
)

# Statements that a previously-reported problem is over.
_RESOLVED_RE = re.compile(
    r"\b(?:fixed|resolved|unblocked|closed|merged|back up|green now|"
    r"no longer|anymore|it works now)\b",
    re.I,
)

_QUOTE_VERB_RE = re.compile(
    r"\b(?:said|says|wrote|writes|quoting|quoted|according to)\b[^\"\u201c]{0,40}"
    r"[\"\u201c][^\"\u201d]{3,}[\"\u201d]",
    re.I,
)
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_FENCE_RE = re.compile(r"```.*?```", re.S)

_AT_MENTION_RE = re.compile(r"@([A-Za-z0-9._-]+)")
_ASSIGNED_RE = re.compile(r"\bassigned to ([A-Za-z][A-Za-z0-9._-]*)", re.I)
_OWNER_RE = re.compile(r"\bowner:\s*([A-Za-z][A-Za-z0-9._-]*)", re.I)
_NAMED_ACTOR_RE = re.compile(
    r"\b(?!(?:We|It|They|This|That|There|He|She|You|I)\b)"
    r"([A-Z][A-Za-z0-9._-]*)\s+(?:will|is going to|is handling|can|to)\b"
)
_FIRST_PERSON_RE = re.compile(r"\b(?:i'?ll|i will|i'm going to|i can)\b", re.I)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


@dataclass
class ExtractedItem:
    category: str
    text: str
    msg_index: int
    speaker: Optional[str]
    owner: Optional[str]
    confidence: float
    cues: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "text": self.text,
            "msg_index": self.msg_index,
            "speaker": self.speaker,
            "owner": self.owner,
            "confidence": self.confidence,
            "cues": list(self.cues),
        }


def strip_quoted(text: str) -> str:
    """Remove text that reports someone else's words rather than the author's."""
    if not text:
        return ""
    lines = [line for line in text.splitlines() if not line.lstrip().startswith(">")]
    cleaned = "\n".join(lines)
    cleaned = _FENCE_RE.sub(" ", cleaned)
    cleaned = _INLINE_CODE_RE.sub(" ", cleaned)
    cleaned = _QUOTE_VERB_RE.sub(" ", cleaned)
    return cleaned


def _clause_before(sentence: str, start: int, window: int = 45) -> str:
    prefix = sentence[max(0, start - window) : start]
    return re.split(r"[.;,]\s", prefix)[-1]


def _is_negated(sentence: str, start: int) -> bool:
    return bool(_NEGATION_RE.search(_clause_before(sentence, start)))


def _is_resolved(sentence: str) -> bool:
    return bool(_RESOLVED_RE.search(sentence))


def _split_sentences(text: str) -> Iterable[str]:
    for part in _SENTENCE_SPLIT_RE.split(text):
        part = part.strip(" \t-*\u2022")
        if part:
            yield part


def detect_owner(sentence: str, speaker: Optional[str]) -> Optional[str]:
    match = _AT_MENTION_RE.search(sentence)
    if match:
        return _normalize_owner(match.group(1))
    match = _OWNER_RE.search(sentence)
    if match:
        return _normalize_owner(match.group(1))
    match = _ASSIGNED_RE.search(sentence)
    if match:
        return _normalize_owner(match.group(1))
    match = _NAMED_ACTOR_RE.search(sentence)
    if match:
        return _normalize_owner(match.group(1))
    if _FIRST_PERSON_RE.search(sentence) and speaker:
        return _normalize_owner(speaker)
    return None


def _normalize_owner(value: str) -> str:
    return value.strip().strip(".,:;!?").lstrip("@").lower()


def _adjust_confidence(confidence: float, sentence: str, category: str) -> float:
    score = confidence
    if sentence.rstrip().endswith("?"):
        score -= 0.15 if category != "action_item" else 0.10
    if category in ("blocker", "bug") and _RESOLVED_RE.search(sentence):
        score -= 0.30
    return round(max(0.05, min(0.99, score)), 2)


class RuleExtractor:
    """Keyword/cue extraction with negation, quote handling and owner detection."""

    def __init__(self, min_confidence: float = 0.0):
        self.min_confidence = min_confidence

    def extract(self, messages: List[Dict[str, Any]]) -> List[ExtractedItem]:
        # One item per (message, category) keeps a chatty message from flooding
        # the report with three near-identical lines.
        best: Dict[tuple[int, str], ExtractedItem] = {}
        for index, message in enumerate(messages):
            if not isinstance(message, dict):
                continue
            text = (message.get("text") or "").strip()
            if not text:
                continue
            cleaned = strip_quoted(text)
            if not cleaned.strip():
                continue
            speaker = (message.get("user") or message.get("username") or "").strip() or None
            for sentence in _split_sentences(cleaned):
                for category in CATEGORIES:
                    hit = self._match(sentence, category)
                    if not hit:
                        continue
                    cue, confidence = hit
                    if confidence < self.min_confidence:
                        continue
                    owner = detect_owner(sentence, speaker)
                    item = ExtractedItem(
                        category=category,
                        text=text,
                        msg_index=index,
                        speaker=speaker,
                        owner=owner,
                        confidence=confidence,
                        cues=[cue],
                    )
                    key = (index, category)
                    previous = best.get(key)
                    if previous is None or item.confidence > previous.confidence:
                        best[key] = item
                    elif owner and not previous.owner:
                        previous.owner = owner
        return sorted(best.values(), key=lambda item: (item.msg_index, CATEGORIES.index(item.category)))

    def _match(self, sentence: str, category: str) -> Optional[tuple[str, float]]:
        for pattern, strength in _CUES[category]:
            for match in re.finditer(pattern, sentence, re.I):
                if category in ("blocker", "bug", "feature_request") and _is_resolved(sentence):
                    continue
                # Decisions may legitimately be negative ("we decided not to ship").
                if category != "decision" and _is_negated(sentence, match.start()):
                    continue
                return match.group(0).lower(), _adjust_confidence(strength, sentence, category)
        return None

    def summarize(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        items = self.extract(messages)
        buckets: Dict[str, List[Dict[str, Any]]] = {
            "blockers": [],
            "action_items": [],
            "decisions": [],
            "bugs": [],
            "feature_requests": [],
        }
        names = {
            "blocker": "blockers",
            "action_item": "action_items",
            "decision": "decisions",
            "bug": "bugs",
            "feature_request": "feature_requests",
        }
        for item in items:
            buckets[names[item.category]].append(item.as_dict())
        buckets["item_count"] = len(items)
        return buckets


def extract_items(messages: List[Dict[str, Any]], min_confidence: float = 0.0) -> List[ExtractedItem]:
    return RuleExtractor(min_confidence=min_confidence).extract(messages)
