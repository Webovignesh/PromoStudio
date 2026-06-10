from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import shutil

from ..database import get_db
from ..models import AppSettings
from ..config import settings as app_settings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    key: str
    value: str


@router.get("/")
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get all application settings."""
    result = await db.execute(select(AppSettings))
    db_settings = result.scalars().all()

    settings_dict = {s.key: s.value for s in db_settings}

    # Include defaults from config
    return {
        "lm_studio_url": settings_dict.get("lm_studio_url", app_settings.lm_studio_url),
        "storage_path": settings_dict.get("storage_path", app_settings.storage_path),
        "ffmpeg_path": settings_dict.get("ffmpeg_path", app_settings.ffmpeg_path),
        "default_format": settings_dict.get("default_format", "mp4"),
        "default_quality": settings_dict.get("default_quality", "high"),
    }


@router.put("/")
async def update_settings(updates: list[SettingsUpdate], db: AsyncSession = Depends(get_db)):
    """Update application settings."""
    for update in updates:
        result = await db.execute(
            select(AppSettings).where(AppSettings.key == update.key)
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = update.value
        else:
            setting = AppSettings(key=update.key, value=update.value)
            db.add(setting)
    return {"message": "Settings updated"}


@router.get("/lm-studio/status")
async def check_lm_studio():
    """Check LM Studio connection status."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{app_settings.lm_studio_url}/models")
            if response.status_code == 200:
                return {"connected": True, "models": response.json()}
            return {"connected": False, "error": f"Status {response.status_code}"}
    except Exception as e:
        return {"connected": False, "error": str(e)}


@router.get("/ffmpeg/status")
async def check_ffmpeg():
    """Check FFmpeg availability."""
    ffmpeg_path = shutil.which(app_settings.ffmpeg_path)
    if ffmpeg_path:
        import subprocess

        try:
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version_line = result.stdout.split("\n")[0] if result.stdout else "Unknown"
            return {"available": True, "path": ffmpeg_path, "version": version_line}
        except Exception as e:
            return {"available": False, "error": str(e)}
    return {"available": False, "error": "FFmpeg not found in PATH"}
