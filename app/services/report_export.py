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


def _confidence(item: Any) -> Optional[float]:
    value = _value(item, "confidence")
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, number))


def _confidence_suffix(item: Any) -> str:
    value = _confidence(item)
    if value is None:
        return ""
    return f" · {round(value * 100)}% confidence"


def _line(item: Any) -> str:
    description = _value(item, "description") or _value(item, "title") or ""
    owner = _owner(item)
    base = f"{description} ({owner})" if owner else description
    return f"{base}{_confidence_suffix(item)}"


def provenance(report: Any) -> str:
    """A line that travels with the report instead of staying in the UI banner."""
    provider = str(_value(report, "ai_provider") or "").strip()
    model = _value(report, "ai_model")
    if provider == "rules":
        return (
            "Rule-based output - no AI model was used. Every item comes from explicit "
            "cue words. Confidence scores reflect cue strength, not probability."
        )
    if provider:
        suffix = f" ({model})" if model else ""
        return (
            f"Generated with {provider}{suffix}. Confidence scores are model-reported, "
            "not calibrated probabilities."
        )
    return (
        "Provenance unknown: this report does not record which extractor produced it. "
        "Confidence scores, where present, are not probabilities."
    )


def render_markdown(report: Any, items: Iterable[Any]) -> str:
    title = _value(report, "title") or "Status report"
    summary = _value(report, "executive_summary")
    lines = [f"# {title}", ""]
    if summary:
        lines += [summary, ""]
    lines += [f"> {provenance(report)}", ""]
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
    lines += ["", f"_{provenance(report)}_"]
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
    lines += ["—", provenance(report), "Sent from Auto-Reporter"]
    return "\n".join(lines)


def render(report: Any, items: Iterable[Any], export_format: str) -> str:
    if export_format == "markdown":
        return render_markdown(report, items)
    if export_format == "slack":
        return render_slack(report, items)
    if export_format == "email":
        return render_email(report, items)
    raise ValueError(f"Unsupported export format: {export_format}")
