from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from ..database import get_db
from ..models import Promo, Show

router = APIRouter(prefix="/promos", tags=["promos"])


class PromoRequest(BaseModel):
    show_id: int
    episode_id: int | None = None
    ad_type: str = "ep-cut"
    duration: float = 30.0
    aspect_ratio: str = "9:16"
    mode: str = "review_first"
    bgm_enabled: bool = True
    sfx_enabled: bool = True
    normalize_audio: bool = True
    include_cta: bool = False
    include_logo: bool = False


class ExportRequest(BaseModel):
    promo_id: int
    format: str = "mp4"
    quality: str = "high"


@router.post("/generate")
async def generate_promo(request: PromoRequest, db: AsyncSession = Depends(get_db)):
    """Generate a new promo."""
    # Verify show exists
    result = await db.execute(select(Show).where(Show.id == request.show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    promo = Promo(
        show_id=request.show_id,
        episode_id=request.episode_id,
        ad_type=request.ad_type,
        duration=request.duration,
        aspect_ratio=request.aspect_ratio,
        mode=request.mode,
        status="processing",
    )
    db.add(promo)
    await db.flush()

    # In a real implementation, this would trigger async promo generation
    # For now, we return the promo with processing status
    return {
        "id": promo.id,
        "show_id": promo.show_id,
        "status": promo.status,
        "message": "Promo generation started",
    }


@router.post("/export")
async def export_promo(request: ExportRequest, db: AsyncSession = Depends(get_db)):
    """Export a generated promo."""
    result = await db.execute(select(Promo).where(Promo.id == request.promo_id))
    promo = result.scalar_one_or_none()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo not found")
    if promo.status != "ready":
        raise HTTPException(status_code=400, detail="Promo is not ready for export")

    return {
        "id": promo.id,
        "output_path": promo.output_path,
        "format": request.format,
        "quality": request.quality,
        "message": "Export started",
    }
