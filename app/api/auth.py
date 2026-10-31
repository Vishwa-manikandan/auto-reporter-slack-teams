from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("/slack/callback")
async def slack_callback(code: str, db: Session = Depends(get_db)):
    # OAuth flow implementation
    return {"message": "Slack OAuth callback", "code": code}


@router.get("/slack/install")
async def slack_install():
    return {"message": "Slack install URL", "url": "https://slack.com/oauth/v2/authorize"}
