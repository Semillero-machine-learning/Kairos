"""System endpoints mounted at the root, outside /api/v1.

/health runs a SELECT 1 so it doubles as a liveness probe and as the request
that keeps Render and Supabase awake (RNF-02, RNF-07).
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(tags=["system"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
