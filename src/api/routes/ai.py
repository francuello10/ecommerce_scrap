"""
src/api/routes/ai.py
====================
AI management routes (test connection, etc.).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_session
from core.models import AIGeneratorSettings
from core.ai.factory import AIFactory

router = APIRouter(prefix="/ai", tags=["AI"])

class TestConnectionRequest(BaseModel):
    model_name: str
    api_key: str | None = None
    settings_id: int | None = None

@router.post("/test-connection")
async def test_connection(
    req: TestConnectionRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Test connectivity with a given AI provider.
    """
    api_key = req.api_key
    model_name = req.model_name
    
    # If settings_id provided, load from DB if api_key is missing
    if req.settings_id and not api_key:
        res = await session.execute(
            select(AIGeneratorSettings).where(AIGeneratorSettings.id == req.settings_id)
        )
        settings = res.scalar_one_or_none()
        if not settings:
            raise HTTPException(status_code=404, detail="Settings not found")
        model_name = settings.model_name
        # Note: In production we'd decrypt or use a dedicated key store
        # but for this MVP we'll assume it's set in req or env if not in settings.
        # Searching for key matches...
    
    try:
        provider = AIFactory.create(model_name=model_name, api_key=api_key)
        success = await provider.test_connection()
        if not success:
            return {"success": False, "message": "Failed to connect. Check API key and model name."}
        return {"success": True, "message": f"Successfully connected to {model_name}"}
    except Exception as e:
        return {"success": False, "message": str(e)}
