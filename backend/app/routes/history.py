from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc

from ..database import get_db
from ..models import Promo, Show

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/")
async def list_promos(
    show_id: int | None = None,
    status: str | None = None,
    ad_type: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List generated promos with filters and sorting."""
    query = select(Promo)

    # Apply filters
    if show_id:
        query = query.where(Promo.show_id == show_id)
    if status:
        query = query.where(Promo.status == status)
    if ad_type:
        query = query.where(Promo.ad_type == ad_type)

    # Apply sorting
    sort_column = getattr(Promo, sort_by, Promo.created_at)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Apply pagination
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    promos = result.scalars().all()

    return [
        {
            "id": promo.id,
            "show_id": promo.show_id,
            "episode_id": promo.episode_id,
            "ad_type": promo.ad_type,
            "duration": promo.duration,
            "aspect_ratio": promo.aspect_ratio,
            "mode": promo.mode,
            "status": promo.status,
            "output_path": promo.output_path,
            "thumbnail": promo.thumbnail,
            "created_at": promo.created_at.isoformat() if promo.created_at else None,
        }
        for promo in promos
    ]


@router.delete("/{promo_id}")
async def delete_promo(promo_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a promo from history."""
    result = await db.execute(select(Promo).where(Promo.id == promo_id))
    promo = result.scalar_one_or_none()
    if not promo:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Promo not found")
    await db.delete(promo)
    return {"message": "Promo deleted"}
