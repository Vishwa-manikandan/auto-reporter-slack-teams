from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.report_generator import ReportGenerator
from app.models.channel import Channel

router = APIRouter()


@router.post("/generate/daily")
async def generate_daily_report(workspace_id: int = None, channel_id: int = None, db: Session = Depends(get_db)):
    generator = ReportGenerator(db=db)
    try:
        if channel_id:
            report = await generator.generate_daily_report(channel_id=channel_id)
        elif workspace_id:
            # Try first selected channel
            channel = db.query(Channel).filter(Channel.workspace_id == workspace_id, Channel.is_selected == True).first()
            if not channel:
                channel = db.query(Channel).filter(Channel.workspace_id == workspace_id).first()
            if not channel:
                raise HTTPException(status_code=404, detail="No channels found for workspace")
            report = await generator.generate_daily_report(channel_id=channel.id)
        else:
            raise HTTPException(status_code=400, detail="workspace_id or channel_id required")
        return {"report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/weekly")
async def generate_weekly_report(workspace_id: int = None, channel_id: int = None, db: Session = Depends(get_db)):
    generator = ReportGenerator(db=db)
    try:
        if channel_id:
            report = await generator.generate_weekly_report(channel_id=channel_id)
        elif workspace_id:
            channel = db.query(Channel).filter(Channel.workspace_id == workspace_id, Channel.is_selected == True).first()
            if not channel:
                channel = db.query(Channel).filter(Channel.workspace_id == workspace_id).first()
            if not channel:
                raise HTTPException(status_code=404, detail="No channels found for workspace")
            report = await generator.generate_weekly_report(channel_id=channel.id)
        else:
            raise HTTPException(status_code=400, detail="workspace_id or channel_id required")
        return {"report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_reports(workspace_id: int = None, db: Session = Depends(get_db)):
    return {"reports": []}


@router.get("/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    return {"report": None}
