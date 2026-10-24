from fastapi import APIRouter
from src.routes.chat import router as chat_router
from src.routes.health import router as health_router

router = APIRouter()

# Compose API endpoints in their existing registration order.
router.include_router(health_router)
router.include_router(chat_router)
