from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "healthy", "database": "ok"})
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "unhealthy", "database": "error"})


@app.on_event("shutdown")
async def shutdown_event():
    try:
        # Attempt cleanup of any shared Slack clients if present
        pass
    except Exception:
        pass



@app.on_event("startup")
async def startup_event():
    try:
        from app.db.session import engine
        from app.db.session import Base
        import app.models  # ensure models are imported
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass
