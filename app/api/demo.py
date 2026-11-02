"""Generate a report from pasted messages, without needing a live Slack app.

This is what the web UI at /ui/ calls. It exists so the product can be
demonstrated and evaluated end to end: the report is persisted like any other,
so done-state and edits survive a page refresh.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.report import Report
from app.models.report_item import ReportItem
from app.services.ai_provider import AIProviderFactory
from app.services.ai_status import provider_status
from app.services.report_export import serialize_item, serialize_report
from app.services.rule_extractor import RuleExtractor

router = APIRouter()

KEY_TO_CATEGORY = {
    "blockers": "blocker",
    "action_items": "action_item",
    "decisions": "decision",
    "bugs": "bug",
    "feature_requests": "feature_request",
}

AI_PROMPT = (
    "You extract status items from Slack messages. Return ONLY a JSON object with "
    "keys blockers, action_items, decisions, bugs, feature_requests. Each value is "
    "an array of objects with keys: text (string, quote or closely paraphrase the "
    "message), owner (string or null), msg_index (zero-based index of the supporting "
    "message), confidence (0-1). Include only items supported by the messages. "
    "Never invent owners or facts."
)


class DemoMessage(BaseModel):
    user: Optional[str] = None
    text: str = Field(min_length=1, max_length=8000)
    ts: Optional[str] = None


class DemoReportRequest(BaseModel):
    messages: List[DemoMessage] = Field(min_length=1, max_length=500)
    report_type: str = "daily"
    title: Optional[str] = None
    provider: Optional[str] = None


def _dump(message: DemoMessage) -> Dict[str, Any]:
    if hasattr(message, "model_dump"):
        return message.model_dump()
    return message.dict()


def _rule_items(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [item.as_dict() for item in RuleExtractor().extract(messages)]


def _parse_json(raw: str) -> Dict[str, Any]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("model did not return a JSON object")
    return data


def _ai_items(payload: Dict[str, Any], messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for key, category in KEY_TO_CATEGORY.items():
        entries = payload.get(key) or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, str):
                entry = {"text": entry}
            if not isinstance(entry, dict):
                continue
            text = (entry.get("text") or "").strip()
            if not text:
                continue
            index = entry.get("msg_index")
            if not isinstance(index, int) or not (0 <= index < len(messages)):
                index = None
            owner = entry.get("owner")
            if isinstance(owner, str) and owner.strip():
                owner = owner.strip().lstrip("@").lower()
            else:
                owner = None
            confidence = entry.get("confidence", 0.85)
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = 0.85
            items.append(
                {
                    "category": category,
                    "text": text,
                    "msg_index": index,
                    "speaker": messages[index].get("user") if index is not None else None,
                    "owner": owner,
                    "confidence": round(max(0.0, min(1.0, confidence)), 2),
                    "cues": ["ai"],
                }
            )
    return items


def _summary(messages: int, items: List[Dict[str, Any]]) -> str:
    counts: Dict[str, int] = {}
    for item in items:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    labels = {
        "blocker": "blocker",
        "action_item": "action item",
        "decision": "decision",
        "bug": "bug",
        "feature_request": "feature request",
    }
    parts = []
    for category, label in labels.items():
        count = counts.get(category, 0)
        if count:
            parts.append(f"{count} {label}{'' if count == 1 else 's'}")
    if not parts:
        return f"{messages} messages analysed. No blockers, action items or decisions detected."
    return f"{messages} messages analysed: " + ", ".join(parts) + "."


@router.post("/report")
async def generate_demo_report(payload: DemoReportRequest, db: Session = Depends(get_db)):
    if payload.report_type not in ("daily", "weekly"):
        raise HTTPException(status_code=400, detail="report_type must be 'daily' or 'weekly'")

    messages = [_dump(message) for message in payload.messages]
    status = provider_status()
    mode = "ai" if status["live"] else "rules"
    warning = None
    items: List[Dict[str, Any]] = []

    if mode == "ai":
        try:
            provider = AIProviderFactory.create(payload.provider or status["provider"])
            raw = await provider.generate(
                [{"index": index, "user": m.get("user"), "text": m.get("text")} for index, m in enumerate(messages)],
                AI_PROMPT,
            )
            items = _ai_items(_parse_json(raw), messages)
        except Exception as exc:  # fall back rather than losing the request
            mode = "rules"
            warning = f"{status['provider']} call failed ({type(exc).__name__}); used deterministic rules instead."

    if mode == "rules":
        items = _rule_items(messages)

    items.sort(key=lambda item: (item["msg_index"] if item["msg_index"] is not None else 10**6))
    summary = _summary(len(messages), items)

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1 if payload.report_type == "daily" else 7)
    title = payload.title or f"{payload.report_type.capitalize()} report"

    report = Report(
        channel_id=None,
        workspace_id=None,
        report_type=payload.report_type,
        period_start=start_time,
        period_end=end_time,
        title=title,
        executive_summary=summary,
        status="completed",
        ai_provider=status["provider"] if mode == "ai" else "rules",
        ai_model=status["model"] if mode == "ai" else None,
        report_data={
            "mode": mode,
            "requested_provider": status["requested_provider"],
            "message_count": len(messages),
            "counts": {category: sum(1 for item in items if item["category"] == category) for category in KEY_TO_CATEGORY.values()},
        },
    )
    db.add(report)
    db.flush()

    for position, item in enumerate(items):
        references = []
        if item["msg_index"] is not None:
            references.append(
                {
                    "msg_index": item["msg_index"],
                    "speaker": item.get("speaker"),
                    "cues": item.get("cues", []),
                }
            )
        db.add(
            ReportItem(
                report_id=report.id,
                category=item["category"],
                description=item["text"],
                assignee=item.get("owner"),
                confidence=item.get("confidence"),
                position=position,
                source_references=references or None,
                done=False,
            )
        )

    db.commit()
    db.refresh(report)
    stored = (
        db.query(ReportItem)
        .filter(ReportItem.report_id == report.id)
        .order_by(ReportItem.position.asc(), ReportItem.id.asc())
        .all()
    )
    return {
        "report_id": report.id,
        "report": serialize_report(report),
        "items": [serialize_item(item) for item in stored],
        "mode": mode,
        "provider": status,
        "message_count": len(messages),
        "warning": warning,
    }
