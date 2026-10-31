from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("/workspaces")
async def list_workspaces(db: Session = Depends(get_db)):
    return {"workspaces": []}


@router.get("/channels")
async def list_channels(workspace_id: int, db: Session = Depends(get_db)):
    return {"channels": []}


@router.post("/channels/select")
async def select_channels(channel_ids: list[int], db: Session = Depends(get_db)):
    return {"message": "Channels selected", "count": len(channel_ids)}
