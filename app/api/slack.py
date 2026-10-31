from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.slack_service import (
    SlackAuthError,
    SlackPermissionError,
    SlackRateLimitError,
    SlackService,
    SlackServiceError,
)

router = APIRouter()


def get_slack_service() -> SlackService:
    try:
        return SlackService()
    except SlackAuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


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
    return {"message": "Channels selected", "count": len(channel_ids)}
