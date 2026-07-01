from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_redis
from ..config import settings
from ..database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    db_ok = False
    redis_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    try:
        get_redis().ping()
        redis_ok = True
    except Exception:
        pass
    return {
        "status": "ok" if db_ok and redis_ok else "degraded",
        "db": db_ok,
        "redis": redis_ok,
        "version": settings.APP_VERSION,
        "stage": settings.STAGE,
        "evolution_enabled": settings.EVOLUTION_ENABLED,
        "feature_sige_enabled": settings.FEATURE_SIGE_ENABLED,
    }
