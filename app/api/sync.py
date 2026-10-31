from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.sync_service import SyncService
from app.models.channel import Channel
from app.models.workspace import Workspace
from app.models.sync_state import SyncState

router = APIRouter()


@router.post("/start")
async def start_sync(workspace_id: int = None, channel_id: int = None, db: Session = Depends(get_db)):
    sync_service = SyncService(db)
    if channel_id:
        result = await sync_service.incremental_sync(channel_id)
        return result
    if workspace_id:
        channels = db.query(Channel).filter(Channel.workspace_id == workspace_id, Channel.is_selected == True).all()
        results = []
        for ch in channels:
            res = await sync_service.incremental_sync(ch.id)
            results.append({"channel_id": ch.id, "result": res})
        return {"workspace_id": workspace_id, "results": results}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id or channel_id required")


@router.get("/status")
async def sync_status(workspace_id: int = None, db: Session = Depends(get_db)):
    if workspace_id:
        channels = db.query(Channel).filter(Channel.workspace_id == workspace_id).all()
        statuses = []
        for ch in channels:
            state = db.query(SyncState).filter(SyncState.channel_id == ch.id).first()
            statuses.append({
                "channel_id": ch.id,
                "channel_name": ch.name,
                "last_sync": state.synced_at.isoformat() if state and state.synced_at else None,
                "last_sync_ts": state.last_sync_ts if state else None,
            })
        return {"workspace_id": workspace_id, "channels": statuses}
    return {"status": "idle", "last_sync": None}


@router.get("/{workspace_id}/status")
async def sync_status_workspace(workspace_id: int, db: Session = Depends(get_db)):
    return await sync_status(workspace_id=workspace_id, db=db)


@router.get("/{workspace_id}/channels")
async def sync_workspace_channels(workspace_id: int, db: Session = Depends(get_db)):
    channels = db.query(Channel).filter(Channel.workspace_id == workspace_id).all()
    return {"channels": [{"id": c.id, "slack_channel_id": c.slack_channel_id, "name": c.name, "is_selected": c.is_selected} for c in channels]}


@router.post("/{workspace_id}/channels/{channel_id}")
async def select_channel(workspace_id: int, channel_id: int, selected: bool = True, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id, Channel.workspace_id == workspace_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    channel.is_selected = selected
    db.commit()
    return {"message": "Channel selection updated", "channel_id": channel_id, "is_selected": selected}


@router.get("/messages")
async def get_messages(channel_id: int, limit: int = 100, db: Session = Depends(get_db)):
    from app.models.message import Message
    messages = db.query(Message).filter(Message.channel_id == channel_id).order_by(Message.id.desc()).limit(limit).all()
    return {"messages": [{"id": m.id, "slack_message_ts": m.slack_message_ts, "text": m.text, "thread_ts": m.thread_ts} for m in reversed(messages)], "count": len(messages)}
