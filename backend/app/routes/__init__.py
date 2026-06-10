from fastapi import APIRouter

from .shows import router as shows_router
from .episodes import router as episodes_router
from .promos import router as promos_router
from .history import router as history_router
from .settings import router as settings_router

api_router = APIRouter(prefix="/api")
api_router.include_router(shows_router)
api_router.include_router(episodes_router)
api_router.include_router(promos_router)
api_router.include_router(history_router)
api_router.include_router(settings_router)
