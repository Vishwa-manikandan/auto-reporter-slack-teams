import logging
import os
from pathlib import Path

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.api import api_router
from app.core.config import settings
from app.db.migrate import ensure_schema
from app.db.session import Base, check_db_connection, engine

logger = logging.getLogger("auto_reporter")

app = FastAPI(
    title="Auto-Reporter API",
    description="Auto-Reporter for Slack Teams - status reports from Slack conversations",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

web_dir = Path(__file__).parent.parent / "web"
if not web_dir.exists():
    web_dir = Path(os.getcwd()) / "web"


@app.get("/ui")
@app.get("/ui/")
async def serve_ui():
    index_path = web_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(status_code=404, content={"detail": "Web UI not found"})


@app.get("/")
async def root():
    return {"message": "Auto-Reporter API", "version": "1.0.0", "status": "healthy"}


@app.get("/health")
async def health():
    db_ok = check_db_connection()
    if db_ok:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "healthy", "database": "ok"},
        )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "unhealthy", "database": "error"},
    )


@app.on_event("startup")
async def startup_event():
    import app.models  # noqa: F401  (registers models on Base.metadata)

    Base.metadata.create_all(bind=engine)
    applied = ensure_schema(engine)
    if applied:
        logger.info("Applied schema additions: %s", ", ".join(applied))
