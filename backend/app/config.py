from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LM Studio configuration
    lm_studio_url: str = "http://localhost:1234/v1"

    # Storage paths
    storage_path: str = str(Path("/projects/sandbox/PromoStudio/Designs"))
    assets_cache_path: str = str(Path("/projects/sandbox/PromoStudio/assets_cache"))

    # FFmpeg
    ffmpeg_path: str = "ffmpeg"

    # Database
    database_url: str = "sqlite+aiosqlite:////projects/sandbox/PromoStudio/promo_tool.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_prefix = "PROMO_"
        env_file = ".env"


settings = Settings()
