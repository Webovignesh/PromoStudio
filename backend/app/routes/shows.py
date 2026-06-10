from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..database import get_db
from ..models import Show

router = APIRouter(prefix="/shows", tags=["shows"])


@router.get("/", response_model=None)
async def list_shows(db: AsyncSession = Depends(get_db)):
    """List all shows."""
    result = await db.execute(select(Show).order_by(Show.created_at.desc()))
    shows = result.scalars().all()
    return [
        {
            "id": show.id,
            "name": show.name,
            "thumbnail": show.thumbnail,
            "has_cta": show.has_cta,
            "has_logo": show.has_logo,
            "episode_count": len(show.episodes) if show.episodes else 0,
            "created_at": show.created_at.isoformat() if show.created_at else None,
        }
        for show in shows
    ]


@router.post("/")
async def create_show(
    name: str,
    thumbnail: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    """Create a new show with optional thumbnail upload."""
    thumbnail_path = None
    if thumbnail:
        # Save thumbnail to storage
        import os
        from ..config import settings

        upload_dir = os.path.join(settings.storage_path, "thumbnails")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, thumbnail.filename)
        content = await thumbnail.read()
        with open(file_path, "wb") as f:
            f.write(content)
        thumbnail_path = f"/thumbnails/{thumbnail.filename}"

    show = Show(name=name, thumbnail=thumbnail_path)
    db.add(show)
    await db.flush()
    return {"id": show.id, "name": show.name, "thumbnail": show.thumbnail}


@router.get("/{show_id}")
async def get_show(show_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific show by ID."""
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    return {
        "id": show.id,
        "name": show.name,
        "thumbnail": show.thumbnail,
        "has_cta": show.has_cta,
        "has_logo": show.has_logo,
        "created_at": show.created_at.isoformat() if show.created_at else None,
    }


@router.delete("/{show_id}")
async def delete_show(show_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a show and all associated data."""
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    await db.delete(show)
    return {"message": "Show deleted"}
