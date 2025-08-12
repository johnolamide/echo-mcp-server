# FastAPI routers
from .auth import router as auth_router
from .chat import router as chat_router
from .services import router as services_router
from .admin import router as admin_router

__all__ = ["auth_router", "chat_router", "services_router", "admin_router"]