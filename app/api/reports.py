from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.channel import Channel
from app.models.correction import Correction
from app.models.report import Report
from app.models.report_item import ReportItem
from app.services.ai_status import provider_status
from app.services.report_export import (
    EXPORT_FORMATS,
    render,
    serialize_item,
    serialize_report,
)
from app.services.report_generator import ReportGenerator
from app.services.rule_extractor import RuleExtractor

router = APIRouter()

CATEGORY_KEYS = {
    "blockers": "blocker",
    "action_items": "action_item",
    "decisions": "decision",
    "bugs": "bug",
    "feature_requests": "feature_request",
}


class ItemUpdate(BaseModel):
    done: Optional[bool] = None
    description: Optional[str] = None
    title: Optional[str] = None
    assignee: Optional[str] = None
    status: Optional[str] = None
    position: Optional[int] = None


class CorrectionCreate(BaseModel):
    verdict: str
    note: Optional[str] = None


def _resolve_channel(db: Session, workspace_id: Optional[int], channel_id: Optional[int]) -> Channel:
    if channel_id:
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
    elif workspace_id:
        channel = (
            db.query(Channel)
            .filter(Channel.workspace_id == workspace_id, Channel.is_selected.is_(True))
            .first()
            or db.query(Channel).filter(Channel.workspace_id == workspace_id).first()
        )
    else:
        raise HTTPException(status_code=400, detail="workspace_id or channel_id required")
    if not channel:
        raise HTTPException(status_code=404, detail="No channels found")
    return channel


def _entry_fields(entry: Any) -> Dict[str, Any]:
    if isinstance(entry, str):
        return {"text": entry, "owner": None, "confidence": None, "msg_index": None}
    if isinstance(entry, dict):
        return {
            "text": entry.get("text") or entry.get("description") or "",
            "owner": entry.get("owner") or entry.get("assignee"),
            "confidence": entry.get("confidence"),
            "msg_index": entry.get("msg_index"),
        }
    return {"text": str(entry), "owner": None, "confidence": None, "msg_index": None}


def _add_items(db: Session, report_id: int, report_data: Dict[str, Any]) -> None:
    position = 0
    for key, category in CATEGORY_KEYS.items():
        for entry in report_data.get(key, []) or []:
            fields = _entry_fields(entry)
            if not fields["text"]:
                continue
            references = None
            if fields["msg_index"] is not None:
                references = [{"msg_index": fields["msg_index"]}]
            db.add(
                ReportItem(
                    report_id=report_id,
                    category=category,
                    description=fields["text"],
                    assignee=fields["owner"],
                    confidence=fields["confidence"],
                    position=position,
                    source_references=references,
                )
            )
            position += 1


def _rule_report_data(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    data = RuleExtractor().summarize(messages)
    counts = {category: len(data[key]) for key, category in CATEGORY_KEYS.items()}
    parts = [f"{count} {category.replace('_', ' ')}{'' if count == 1 else 's'}" for category, count in counts.items() if count]
    if parts:
        data["executive_summary"] = f"{len(messages)} messages analysed: " + ", ".join(parts) + "."
    else:
        data["executive_summary"] = f"{len(messages)} messages analysed. No reportable items detected."
    return data


async def _generate(
    db: Session,
    report_type: str,
    workspace_id: Optional[int],
    channel_id: Optional[int],
    regenerate: bool,
) -> Dict[str, Any]:
    channel = _resolve_channel(db, workspace_id, channel_id)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1 if report_type == "daily" else 7)

    existing = (
        db.query(Report)
        .filter(
            Report.channel_id == channel.id,
            Report.report_type == report_type,
            Report.period_start >= start_time - timedelta(hours=2),
            Report.status == "completed",
        )
        .first()
    )
    if existing and not regenerate:
        return {"report": serialize_report(existing), "message": "existing report found"}

    status = provider_status()
    generator = ReportGenerator(db=db)

    if status["live"]:
        mode = "ai"
        try:
            if report_type == "daily":
                report_data = await generator.generate_daily_report(channel_id=channel.id)
            else:
                report_data = await generator.generate_weekly_report(channel_id=channel.id)
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=502, detail=f"AI generation failed: {exc}")
    else:
        mode = "rules"
        messages = generator.prepare_messages_for_analysis(channel.id, start_time, end_time)
        report_data = _rule_report_data(messages)

    report = Report(
        workspace_id=channel.workspace_id,
        channel_id=channel.id,
        report_type=report_type,
        period_start=start_time,
        period_end=end_time,
        title=f"{report_type.capitalize()} Report - {channel.name or channel.slack_channel_id}",
        executive_summary=report_data.get("executive_summary"),
        status="completed",
        ai_provider=status["provider"] if mode == "ai" else "rules",
        ai_model=status["model"] if mode == "ai" else None,
        report_data={**report_data, "mode": mode},
    )
    db.add(report)
    db.flush()
    _add_items(db, report.id, report_data)
    db.commit()
    db.refresh(report)

    items = (
        db.query(ReportItem)
        .filter(ReportItem.report_id == report.id)
        .order_by(ReportItem.position.asc(), ReportItem.id.asc())
        .all()
    )
    return {
        "report_id": report.id,
        "report": serialize_report(report),
        "items": [serialize_item(item) for item in items],
    }


def _get_report(db: Session, report_id: int) -> Report:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _report_items(db: Session, report_id: int) -> List[ReportItem]:
    return (
        db.query(ReportItem)
        .filter(ReportItem.report_id == report_id)
        .order_by(ReportItem.position.asc(), ReportItem.id.asc())
        .all()
    )


@router.post("/daily")
async def generate_daily_report(
    workspace_id: int = None,
    channel_id: int = None,
    regenerate: bool = False,
    db: Session = Depends(get_db),
):
    return await _generate(db, "daily", workspace_id, channel_id, regenerate)


@router.post("/weekly")
async def generate_weekly_report(
    workspace_id: int = None,
    channel_id: int = None,
    regenerate: bool = False,
    db: Session = Depends(get_db),
):
    return await _generate(db, "weekly", workspace_id, channel_id, regenerate)


@router.get("")
async def list_reports(
    workspace_id: int = None,
    report_type: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Report)
    if workspace_id:
        query = query.filter(Report.workspace_id == workspace_id)
    if report_type:
        query = query.filter(Report.report_type == report_type)
    reports = query.order_by(Report.generated_at.desc()).offset(offset).limit(limit).all()
    return {"reports": [serialize_report(report) for report in reports], "total": query.count()}


@router.get("/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    report = _get_report(db, report_id)
    return {
        "report": serialize_report(report),
        "items": [serialize_item(item) for item in _report_items(db, report_id)],
    }


@router.post("/{report_id}/regenerate")
async def regenerate_report(report_id: int, db: Session = Depends(get_db)):
    report = _get_report(db, report_id)
    if not report.channel_id:
        raise HTTPException(status_code=400, detail="This report is not linked to a Slack channel")
    db.delete(report)
    db.commit()
    return await _generate(db, report.report_type, None, report.channel_id, True)


@router.delete("/{report_id}")
async def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = _get_report(db, report_id)
    db.delete(report)
    db.commit()
    return {"message": "deleted"}


@router.patch("/{report_id}/items/{item_id}")
async def update_item(report_id: int, item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)):
    _get_report(db, report_id)
    item = (
        db.query(ReportItem)
        .filter(ReportItem.id == item_id, ReportItem.report_id == report_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Report item not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "description" and value is not None:
            value = value.strip()
            if not value:
                raise HTTPException(status_code=400, detail="description cannot be empty")
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return {"item": serialize_item(item)}


@router.delete("/{report_id}/items/{item_id}")
async def delete_item(report_id: int, item_id: int, db: Session = Depends(get_db)):
    _get_report(db, report_id)
    item = (
        db.query(ReportItem)
        .filter(ReportItem.id == item_id, ReportItem.report_id == report_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Report item not found")
    db.delete(item)
    db.commit()
    return {"message": "deleted", "item_id": item_id}


@router.post("/{report_id}/items/{item_id}/correction")
async def record_correction(
    report_id: int,
    item_id: int,
    payload: CorrectionCreate,
    db: Session = Depends(get_db),
):
    _get_report(db, report_id)
    item = (
        db.query(ReportItem)
        .filter(ReportItem.id == item_id, ReportItem.report_id == report_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Report item not found")
    if payload.verdict not in ("wrong", "ok"):
        raise HTTPException(status_code=400, detail="verdict must be 'wrong' or 'ok'")

    correction = Correction(report_item_id=item_id, verdict=payload.verdict, note=payload.note)
    db.add(correction)
    if payload.verdict == "wrong":
        item.status = "flagged"
    db.commit()
    db.refresh(correction)
    return {"id": correction.id, "verdict": correction.verdict, "item_status": item.status}


@router.get("/{report_id}/corrections")
async def list_corrections(report_id: int, db: Session = Depends(get_db)):
    _get_report(db, report_id)
    item_ids = [item.id for item in _report_items(db, report_id)]
    corrections = (
        db.query(Correction)
        .filter(Correction.report_item_id.in_(item_ids))
        .order_by(Correction.created_at.desc())
        .all()
    ) if item_ids else []
    return {
        "corrections": [
            {
                "id": correction.id,
                "report_item_id": correction.report_item_id,
                "verdict": correction.verdict,
                "note": correction.note,
                "created_at": correction.created_at.isoformat() if correction.created_at else None,
            }
            for correction in corrections
        ]
    }


@router.get("/{report_id}/export")
async def export_report(report_id: int, format: str = "markdown", db: Session = Depends(get_db)):
    if format not in EXPORT_FORMATS:
        raise HTTPException(status_code=400, detail=f"format must be one of {', '.join(EXPORT_FORMATS)}")
    report = _get_report(db, report_id)
    items = _report_items(db, report_id)
    content = render(report, items, format)
    extension = "md" if format == "markdown" else "txt"
    return {
        "format": format,
        "filename": f"report-{report_id}.{extension}",
        "content": content,
    }
