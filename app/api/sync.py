from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.post("/start")
async def start_sync(workspace_id: int, db: Session = Depends(get_db)):
    return {"message": "Sync started", "status": "in_progress"}


@router.get("/status")
async def sync_status(workspace_id: int, db: Session = Depends(get_db)):
    return {"status": "idle", "last_sync": None}


@router.get("/messages")
async def get_messages(channel_id: int, limit: int = 100, db: Session = Depends(get_db)):
    return {"messages": [], "count": 0}
