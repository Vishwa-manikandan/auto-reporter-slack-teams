from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from slack_sdk.errors import SlackApiError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.channel import Channel
from app.models.report import Report
from app.models.report_item import ReportItem
from app.models.workspace import Workspace
from app.services.encryption_service import EncryptionService
from app.services.report_export import render_slack
from app.services.slack_service import (
    SlackAuthError,
    SlackPermissionError,
    SlackRateLimitError,
    SlackService,
    SlackServiceError,
)

router = APIRouter()


class PostMessageRequest(BaseModel):
    text: Optional[str] = None
    report_id: Optional[int] = None
    channel: Optional[str] = None


def get_slack_service() -> SlackService:
    try:
        return SlackService()
    except SlackAuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


def _resolve_token(db: Session) -> Optional[str]:
    workspace = db.query(Workspace).filter(Workspace.access_token.isnot(None)).first()
    if workspace and workspace.access_token:
        try:
            return EncryptionService().decrypt(workspace.access_token)
        except Exception:
            pass
    return settings.SLACK_BOT_TOKEN or None


@router.get("/status")
@router.get("/connection")
async def check_connection(service: SlackService = Depends(get_slack_service)):
    try:
        workspace_info = await service.get_workspace_info()
        return {"status": "connected", "workspace": workspace_info}
    except SlackAuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except SlackPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except SlackRateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except SlackServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/workspaces")
async def list_workspaces(service: SlackService = Depends(get_slack_service), db: Session = Depends(get_db)):
    try:
        workspace_info = await service.get_workspace_info()
        return {"workspaces": [workspace_info]}
    except SlackAuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except SlackPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except SlackRateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except SlackServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/channels")
async def list_channels(workspace_id: int = None, service: SlackService = Depends(get_slack_service), db: Session = Depends(get_db)):
    try:
        channels = await service.get_channels(include_private=True)
        return {"channels": channels}
    except SlackAuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except SlackPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except SlackRateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except SlackServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/channels/select")
async def select_channels(channel_ids: list[int], db: Session = Depends(get_db)):
    count = 0
    for channel_id in channel_ids:
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if channel:
            channel.is_selected = True
            count += 1
    db.commit()
    return {"message": "Channels selected", "count": count}


@router.post("/post")
async def post_message(payload: PostMessageRequest, db: Session = Depends(get_db)):
    """Send a report (or arbitrary text) back to a Slack channel."""
    text = payload.text
    channel = payload.channel
    report = None

    if payload.report_id is not None:
        report = db.query(Report).filter(Report.id == payload.report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        if not text:
            items = (
                db.query(ReportItem)
                .filter(ReportItem.report_id == report.id)
                .order_by(ReportItem.position.asc(), ReportItem.id.asc())
                .all()
            )
            text = render_slack(report, items)
        if not channel and report.channel_id:
            report_channel = db.query(Channel).filter(Channel.id == report.channel_id).first()
            if report_channel:
                channel = report_channel.slack_channel_id

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Provide text or a report_id to send")
    channel = channel or settings.SLACK_CHANNEL_ID
    if not channel:
        raise HTTPException(status_code=400, detail="No channel selected. Provide a channel id or set SLACK_CHANNEL_ID.")

    token = _resolve_token(db)
    if not token:
        raise HTTPException(
            status_code=400,
            detail="No Slack token configured. Connect a workspace via OAuth or set SLACK_BOT_TOKEN.",
        )

    try:
        service = SlackService(token=token)
    except SlackAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        result = await service.client.chat_postMessage(channel=channel, text=text)
    except SlackApiError as exc:
        error = exc.response.get("error") if exc.response else str(exc)
        raise HTTPException(status_code=502, detail=f"Slack rejected the message: {error}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Slack request failed: {exc}")
    finally:
        await service.close()

    return {"ok": True, "channel": result.get("channel", channel), "ts": result.get("ts")}
