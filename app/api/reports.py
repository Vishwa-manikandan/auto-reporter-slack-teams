from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.db.session import get_db
from app.services.report_generator import ReportGenerator
from app.models.channel import Channel
from app.models.report import Report
from app.models.report_item import ReportItem

router = APIRouter()


@router.post("/daily")
async def generate_daily_report(workspace_id: int = None, channel_id: int = None, regenerate: bool = False, db: Session = Depends(get_db)):
    generator = ReportGenerator(db=db)
    try:
        if channel_id:
            ch = db.query(Channel).filter(Channel.id == channel_id).first()
        elif workspace_id:
            ch = db.query(Channel).filter(Channel.workspace_id == workspace_id, Channel.is_selected == True).first() or db.query(Channel).filter(Channel.workspace_id == workspace_id).first()
        else:
            raise HTTPException(status_code=400, detail="workspace_id or channel_id required")
        if not ch:
            raise HTTPException(status_code=404, detail="No channels found")

        end_time = datetime.utcnow()
        start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0) if False else end_time - __import__('datetime').timedelta(days=1)

        # Check existing
        from datetime import timedelta
        start_time = end_time - timedelta(days=1)
        existing = db.query(Report).filter(
            Report.channel_id == ch.id,
            Report.report_type == "daily",
            Report.period_start >= start_time - timedelta(hours=1),
            Report.status == "completed"
        ).first()
        if existing and not regenerate:
            return {"report": existing, "message": "existing report found"}

        report_data = await generator.generate_daily_report(channel_id=ch.id)
        report = Report(
            workspace_id=ch.workspace_id,
            channel_id=ch.id,
            report_type="daily",
            period_start=start_time,
            period_end=end_time,
            title=f"Daily Report - {ch.name}",
            executive_summary=report_data.get("executive_summary"),
            status="completed",
            report_data=report_data,
        )
        db.add(report)
        db.flush()

        # Persist items
        for item in report_data.get("decisions", []):
            db.add(ReportItem(report_id=report.id, category="decision", description=str(item)))
        for item in report_data.get("action_items", []):
            db.add(ReportItem(report_id=report.id, category="action_item", description=str(item)))
        for item in report_data.get("blockers", []):
            db.add(ReportItem(report_id=report.id, category="blocker", description=str(item)))

        db.commit()
        db.refresh(report)
        return {"report_id": report.id, "report": report}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/weekly")
async def generate_weekly_report(workspace_id: int = None, channel_id: int = None, regenerate: bool = False, db: Session = Depends(get_db)):
    generator = ReportGenerator(db=db)
    try:
        if channel_id:
            ch = db.query(Channel).filter(Channel.id == channel_id).first()
        elif workspace_id:
            ch = db.query(Channel).filter(Channel.workspace_id == workspace_id, Channel.is_selected == True).first() or db.query(Channel).filter(Channel.workspace_id == workspace_id).first()
        else:
            raise HTTPException(status_code=400, detail="workspace_id or channel_id required")
        if not ch:
            raise HTTPException(status_code=404, detail="No channels found")

        from datetime import timedelta
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)

        existing = db.query(Report).filter(
            Report.channel_id == ch.id,
            Report.report_type == "weekly",
            Report.period_start >= start_time - timedelta(hours=2),
            Report.status == "completed"
        ).first()
        if existing and not regenerate:
            return {"report": existing, "message": "existing report found"}

        report_data = await generator.generate_weekly_report(channel_id=ch.id)
        report = Report(
            workspace_id=ch.workspace_id,
            channel_id=ch.id,
            report_type="weekly",
            period_start=start_time,
            period_end=end_time,
            title=f"Weekly Report - {ch.name}",
            executive_summary=report_data.get("executive_summary"),
            status="completed",
            report_data=report_data,
        )
        db.add(report)
        db.flush()

        for item in report_data.get("decisions", []):
            db.add(ReportItem(report_id=report.id, category="decision", description=str(item)))
        for item in report_data.get("action_items", []):
            db.add(ReportItem(report_id=report.id, category="action_item", description=str(item)))
        for item in report_data.get("blockers", []):
            db.add(ReportItem(report_id=report.id, category="blocker", description=str(item)))

        db.commit()
        db.refresh(report)
        return {"report_id": report.id, "report": report}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_reports(workspace_id: int = None, report_type: str = None, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    q = db.query(Report)
    if workspace_id:
        q = q.filter(Report.workspace_id == workspace_id)
    if report_type:
        q = q.filter(Report.report_type == report_type)
    reports = q.order_by(Report.generated_at.desc()).offset(offset).limit(limit).all()
    return {"reports": reports, "total": q.count()}


@router.get("/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    items = db.query(ReportItem).filter(ReportItem.report_id == report_id).all()
    return {"report": report, "items": items}


@router.post("/{report_id}/regenerate")
async def regenerate_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    generator = ReportGenerator(db=db)
    try:
        if report.report_type == "daily":
            report_data = await generator.generate_daily_report(channel_id=report.channel_id)
        else:
            report_data = await generator.generate_weekly_report(channel_id=report.channel_id)
        report.executive_summary = report_data.get("executive_summary")
        report.report_data = report_data
        report.generated_at = datetime.utcnow()
        report.status = "completed"
        db.commit()
        db.refresh(report)
        return {"report_id": report.id, "report": report}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{report_id}")
async def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(report)
    db.commit()
    return {"message": "deleted"}
