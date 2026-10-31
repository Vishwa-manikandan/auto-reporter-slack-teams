from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import api_router
from app.db.session import check_db_connection

app = FastAPI(
    title="Auto-Reporter API",
    description="Auto-Reporter for Slack Teams - AI-powered status reports",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Auto-Reporter API", "version": "1.0.0", "status": "healthy"}


@app.get("/health")
async def health():
    db_ok = check_db_connection()
    if db_ok:
        return {"status": "healthy", "database": "ok"}
    return {"status": "unhealthy", "database": "error"}
