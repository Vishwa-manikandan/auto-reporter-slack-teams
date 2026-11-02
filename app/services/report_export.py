"""Serialize report items and render them for Markdown, Slack and email."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

CATEGORY_ORDER = ("blocker", "action_item", "decision", "bug", "feature_request")

CATEGORY_LABELS = {
    "blocker": "Blockers",
    "action_item": "Action items",
    "decision": "Decisions",
    "bug": "Bugs",
    "feature_request": "Feature requests",
}

EXPORT_FORMATS = ("markdown", "slack", "email")


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def serialize_item(item: Any) -> Dict[str, Any]:
    return {
        "id": _value(item, "id"),
        "report_id": _value(item, "report_id"),
        "category": _value(item, "category"),
        "title": _value(item, "title"),
        "description": _value(item, "description"),
        "assignee": _value(item, "assignee"),
        "status": _value(item, "status"),
        "priority": _value(item, "priority"),
        "done": bool(_value(item, "done", False)),
        "confidence": _value(item, "confidence"),
        "position": _value(item, "position", 0) or 0,
        "source_references": _value(item, "source_references") or [],
    }


def serialize_report(report: Any) -> Dict[str, Any]:
    def iso(value: Any) -> Optional[str]:
        return value.isoformat() if hasattr(value, "isoformat") else value

    return {
        "id": _value(report, "id"),
        "workspace_id": _value(report, "workspace_id"),
        "channel_id": _value(report, "channel_id"),
        "report_type": _value(report, "report_type"),
        "title": _value(report, "title"),
        "executive_summary": _value(report, "executive_summary"),
        "status": _value(report, "status"),
        "period_start": iso(_value(report, "period_start")),
        "period_end": iso(_value(report, "period_end")),
        "generated_at": iso(_value(report, "generated_at")),
        "ai_provider": _value(report, "ai_provider"),
        "ai_model": _value(report, "ai_model"),
        "report_data": _value(report, "report_data"),
    }


def _grouped(items: Iterable[Any]) -> List[tuple[str, List[Any]]]:
    buckets: Dict[str, List[Any]] = {category: [] for category in CATEGORY_ORDER}
    for item in items:
        category = _value(item, "category")
        if category in buckets:
            buckets[category].append(item)
    return [(category, buckets[category]) for category in CATEGORY_ORDER if buckets[category]]


def _owner(item: Any) -> Optional[str]:
    assignee = _value(item, "assignee")
    return f"@{assignee}" if assignee else None


def _line(item: Any) -> str:
    description = _value(item, "description") or _value(item, "title") or ""
    owner = _owner(item)
    return f"{description} ({owner})" if owner else description


def render_markdown(report: Any, items: Iterable[Any]) -> str:
    title = _value(report, "title") or "Status report"
    summary = _value(report, "executive_summary")
    provider = _value(report, "ai_provider")
    lines = [f"# {title}", ""]
    if summary:
        lines += [summary, ""]
    if provider:
        model = _value(report, "ai_model")
        lines += [f"_Generated with {provider}{f' ({model})' if model else ''}._", ""]
    for category, category_items in _grouped(items):
        lines += [f"## {CATEGORY_LABELS[category]}", ""]
        for item in category_items:
            mark = "x" if _value(item, "done", False) else " "
            lines.append(f"- [{mark}] {_line(item)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_slack(report: Any, items: Iterable[Any]) -> str:
    title = _value(report, "title") or "Status report"
    summary = _value(report, "executive_summary")
    lines = [f"*{title}*"]
    if summary:
        lines += ["", summary]
    icons = {
        "blocker": ":rotating_light:",
        "action_item": ":white_check_mark:",
        "decision": ":scales:",
        "bug": ":bug:",
        "feature_request": ":bulb:",
    }
    for category, category_items in _grouped(items):
        lines += ["", f"{icons[category]} *{CATEGORY_LABELS[category]}*"]
        for item in category_items:
            mark = "~" if _value(item, "done", False) else ""
            text = _line(item)
            lines.append(f"• {mark}{text}{mark}")
    return "\n".join(lines)


def render_email(report: Any, items: Iterable[Any]) -> str:
    title = _value(report, "title") or "Status report"
    summary = _value(report, "executive_summary")
    lines = [f"Subject: {title}", "", "Hi team,", ""]
    if summary:
        lines += [summary, ""]
    for category, category_items in _grouped(items):
        lines += [CATEGORY_LABELS[category].upper()]
        for item in category_items:
            mark = "[done] " if _value(item, "done", False) else ""
            lines.append(f"- {mark}{_line(item)}")
        lines.append("")
    lines += ["—", "Sent from Auto-Reporter"]
    return "\n".join(lines)


def render(report: Any, items: Iterable[Any], export_format: str) -> str:
    if export_format == "markdown":
        return render_markdown(report, items)
    if export_format == "slack":
        return render_slack(report, items)
    if export_format == "email":
        return render_email(report, items)
    raise ValueError(f"Unsupported export format: {export_format}")
