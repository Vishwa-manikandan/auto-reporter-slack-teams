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
from app.services.slack_service import SlackService

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
    now = datetime.utcnow()
    # Atomic consumption
    result = db.query(OAuthState).filter(
        OAuthState.state_hash == state_hash,
        OAuthState.used == False,
        OAuthState.expires_at > now,
    ).update({"used": True})
    if result == 0:
        # Check why
        oauth_state = db.query(OAuthState).filter(OAuthState.state_hash == state_hash).first()
        if not oauth_state:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state")
        if oauth_state.used:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State already used")
        if oauth_state.expires_at <= now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expired state")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state")
    db.commit()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": settings.SLACK_CLIENT_ID,
                    "client_secret": settings.SLACK_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.SLACK_REDIRECT_URI,
                },
            )
            if response.status_code != 200:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to exchange OAuth code")
            try:
                data = response.json()
            except Exception:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid OAuth response")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to exchange OAuth code")

    if not isinstance(data, dict) or not data.get("ok"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slack OAuth exchange failed")

    access_token = data.get("access_token") or (data.get("bot") or {}).get("bot_access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No access token received")

    team = data.get("team") or {}
    team_id = team.get("id") or data.get("team_id")
    team_name = team.get("name")
    if not team_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing workspace information")

    try:
        encryption_service = EncryptionService()
        encrypted_token = encryption_service.encrypt(access_token)
    except EncryptionServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token encryption failed")

    try:
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
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to persist workspace")
    return {"message": "Slack workspace connected", "team_id": workspace.slack_team_id, "team_name": workspace.name}


@router.delete("/workspaces/{workspace_id}")
@router.post("/workspaces/{workspace_id}/disconnect")
async def disconnect_workspace(workspace_id: int, db: Session = Depends(get_db)):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    revoked = False
    if workspace.access_token:
        try:
            encryption_service = EncryptionService()
            decrypted_token = encryption_service.decrypt(workspace.access_token)
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    resp = await client.post(
                        "https://slack.com/api/auth.revoke",
                        headers={"Authorization": f"Bearer {decrypted_token}"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, dict) and data.get("ok"):
                            revoked = True
                except Exception:
                    revoked = False
        except Exception:
            revoked = False
    workspace.access_token = None
    db.commit()
    return {"message": "Workspace disconnected", "revoked": revoked}
