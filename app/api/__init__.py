from fastapi import APIRouter

from app.api import ai, auth, demo, reports, slack, sync

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(slack.router, prefix="/slack", tags=["slack"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(demo.router, prefix="/demo", tags=["demo"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
