from .start import router as start_router
from .create_order import router as create_order_router
from .switch_role import router as switch_role_router
from .admin import router as admin_router
from .create_offer import router as create_offer_router
from .manage_offers import router as manage_offers_router
from .fallback import router as fallback_router  # Новый роутер

__all__ = [
    "start_router",
    "create_order_router",
    "switch_role_router",
    "admin_router",
    "create_offer_router",
    "manage_offers_router",
    "fallback_router",  # Добавляем в список
]