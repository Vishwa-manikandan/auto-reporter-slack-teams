from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.report_generator import ReportGenerator

router = APIRouter()
generator = ReportGenerator()


@router.post("/generate/daily")
async def generate_daily_report(workspace_id: int, db: Session = Depends(get_db)):
    # Generate daily report
    report = await generator.generate_daily_report([])
    return {"report": report}


@router.post("/generate/weekly")
async def generate_weekly_report(workspace_id: int, db: Session = Depends(get_db)):
    return {"message": "Weekly report generation"}


@router.get("/")
async def list_reports(workspace_id: int, db: Session = Depends(get_db)):
    return {"reports": []}


@router.get("/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    return {"report": None}
