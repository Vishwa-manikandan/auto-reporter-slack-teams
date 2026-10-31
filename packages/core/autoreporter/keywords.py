"""Keyword detection engine for identifying action items, bugs, blockers."""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DetectedItem:
    """Represents a detected item from Slack messages."""
    type: str  # bug, blocked, action_item, feature_request, other
    text: str
    message_ts: str
    user: Optional[str] = None
    thread_ts: Optional[str] = None
    mentions: List[str] = None
    urgency: str = "medium"  # low, medium, high
    
    def __post_init__(self):
        if self.mentions is None:
            self.mentions = []


class KeywordDetector:
    """Simple rule-based keyword detection."""
    
    PATTERNS = {
        "bug": [
            r"\bbug\b",
            r"\bcrash\b",
            r"\berror\b",
            r"\bfail(s|ed|ing)?\b",
            r"\bbroken\b",
        ],
        "blocked": [
            r"\bblock(ed|ing)?\b",
            r"\bstuck\b",
            r"\bwaiting on\b",
            r"\bcan't proceed\b",
            r"\bcannot proceed\b",
        ],
        "action_item": [
            r"\baction item\b",
            r"\bto[- ]do\b",
            r"\bneed(s|ed)? to\b",
            r"\bplease\b.*\b(do|fix|review|check)\b",
            r"\bassign(ed)? to\b",
        ],
        "feature_request": [
            r"\bfeature request\b",
            r"\brequest\b",
            r"\benhance(ment)?\b",
            r"\badd\b.*\bfeature\b",
        ],
    }
    
    URGENCY_KEYWORDS = {
        "high": [r"\bcritical\b", r"\burgent\b", r"\basap\b", r"\bimmediate(ly)?\b"],
        "low": [r"\blater\b", r"\bnice to have\b", r"\beventually\b"],
    }
    
    def detect(self, message: dict) -> List[DetectedItem]:
        """Detect items in a message."""
        text = message.get("text", "")
        items = []
        
        for item_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    mentions = re.findall(r'<@([A-Z0-9]+)>', text)
                    urgency = self._detect_urgency(text)
                    
                    items.append(DetectedItem(
                        type=item_type,
                        text=text,
                        message_ts=message.get("ts"),
                        user=message.get("user"),
                        thread_ts=message.get("thread_ts"),
                        mentions=mentions,
                        urgency=urgency,
                    ))
                    break  # Only add once per type per message
        
        return items
    
    def _detect_urgency(self, text: str) -> str:
        """Detect urgency level."""
        for level, patterns in self.URGENCY_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return level
        return "medium"
