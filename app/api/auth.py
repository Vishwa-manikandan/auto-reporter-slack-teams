import hashlib
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.oauth_state import OAuthState
from app.models.workspace import Workspace
from app.services.encryption_service import EncryptionService, EncryptionServiceError

router = APIRouter()


def _hash_state(state: str) -> str:
    return hashlib.sha256(state.encode()).hexdigest()


@router.get("/slack/install")
async def slack_install(db: Session = Depends(get_db)):
    if not settings.SLACK_CLIENT_ID or not settings.SLACK_REDIRECT_URI:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slack OAuth is not configured")

    state = secrets.token_urlsafe(32)
    state_hash = _hash_state(state)
    expires_at = datetime.utcnow() + timedelta(seconds=settings.OAUTH_STATE_TTL_SECONDS)

    oauth_state = OAuthState(state_hash=state_hash, expires_at=expires_at, used=False)
    db.add(oauth_state)
    db.commit()

    params = {
        "client_id": settings.SLACK_CLIENT_ID,
        "scope": settings.SLACK_SCOPES,
        "redirect_uri": settings.SLACK_REDIRECT_URI,
        "state": state,
    }
    auth_url = f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/slack/callback")
async def slack_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db),
):
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Slack OAuth denied: {error}")

    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code or state")

    if not settings.SLACK_CLIENT_ID or not settings.SLACK_CLIENT_SECRET or not settings.SLACK_REDIRECT_URI:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slack OAuth is not configured")

    state_hash = _hash_state(state)
    oauth_state = db.query(OAuthState).filter(OAuthState.state_hash == state_hash).first()
    if not oauth_state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state")
    if oauth_state.used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State already used")
    if oauth_state.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expired state")

    oauth_state.used = True
    db.commit()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": settings.SLACK_CLIENT_ID,
                    "client_secret": settings.SLACK_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.SLACK_REDIRECT_URI,
                },
            )
            data = response.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to exchange OAuth code")

    if not data.get("ok"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slack OAuth exchange failed")

    access_token = data.get("access_token") or data.get("bot", {}).get("bot_access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No access token received")

    team = data.get("team") or {}
    team_id = team.get("id") or data.get("team_id")
    team_name = team.get("name")

    try:
        encryption_service = EncryptionService()
        encrypted_token = encryption_service.encrypt(access_token)
    except EncryptionServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    workspace = db.query(Workspace).filter(Workspace.slack_team_id == team_id).first()
    if workspace:
        workspace.access_token = encrypted_token
        if team_name and not workspace.name:
            workspace.name = team_name
    else:
        workspace = Workspace(slack_team_id=team_id, name=team_name, access_token=encrypted_token)
        db.add(workspace)

    db.commit()
    db.refresh(workspace)
    return {"message": "Slack workspace connected", "team_id": workspace.slack_team_id, "team_name": workspace.name}


@router.get("/workspaces")
async def list_workspaces(db: Session = Depends(get_db)):
    workspaces = db.query(Workspace).all()
    result = []
    for ws in workspaces:
        result.append({
            "id": ws.id,
            "slack_team_id": ws.slack_team_id,
            "name": ws.name,
            "connected": bool(ws.access_token),
        })
    return {"workspaces": result}


@router.get("/status")
async def connection_status(db: Session = Depends(get_db)):
    workspaces = db.query(Workspace).all()
    connected = [ws for ws in workspaces if ws.access_token]
    return {"connected": len(connected) > 0, "workspaces": len(connected)}


@router.delete("/workspaces/{workspace_id}")
@router.post("/workspaces/{workspace_id}/disconnect")
async def disconnect_workspace(workspace_id: int, db: Session = Depends(get_db)):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    # Attempt to revoke token if possible (best effort)
    workspace.access_token = None
    db.commit()
    return {"message": "Workspace disconnected"}
