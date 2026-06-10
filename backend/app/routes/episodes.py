from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import Episode, Show

router = APIRouter(prefix="/episodes", tags=["episodes"])


@router.get("/")
async def list_episodes(show_id: int | None = None, db: AsyncSession = Depends(get_db)):
    """List episodes, optionally filtered by show."""
    query = select(Episode).order_by(Episode.created_at.desc())
    if show_id:
        query = query.where(Episode.show_id == show_id)
    result = await db.execute(query)
    episodes = result.scalars().all()
    return [
        {
            "id": ep.id,
            "show_id": ep.show_id,
            "title": ep.title,
            "filename": ep.filename,
            "duration": ep.duration,
            "created_at": ep.created_at.isoformat() if ep.created_at else None,
        }
        for ep in episodes
    ]


@router.post("/")
async def create_episode(
    show_id: int,
    title: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new episode file."""
    # Verify show exists
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    import os
    from ..config import settings

    upload_dir = os.path.join(settings.storage_path, "episodes", str(show_id))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    episode = Episode(
        show_id=show_id,
        title=title,
        filename=file.filename,
    )
    db.add(episode)
    await db.flush()
    return {
        "id": episode.id,
        "show_id": episode.show_id,
        "title": episode.title,
        "filename": episode.filename,
    }


@router.get("/{episode_id}")
async def get_episode(episode_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific episode."""
    result = await db.execute(select(Episode).where(Episode.id == episode_id))
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    return {
        "id": episode.id,
        "show_id": episode.show_id,
        "title": episode.title,
        "filename": episode.filename,
        "duration": episode.duration,
        "created_at": episode.created_at.isoformat() if episode.created_at else None,
    }


@router.delete("/{episode_id}")
async def delete_episode(episode_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an episode."""
    result = await db.execute(select(Episode).where(Episode.id == episode_id))
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    await db.delete(episode)
    return {"message": "Episode deleted"}
