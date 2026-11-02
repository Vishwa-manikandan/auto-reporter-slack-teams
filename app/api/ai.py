from fastapi import APIRouter

from app.services.ai_status import provider_status

router = APIRouter()


@router.get("/status")
async def ai_status():
    """Report the effective AI provider so the UI can label its own output."""
    return provider_status()
