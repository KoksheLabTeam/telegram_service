from .admin.admin_panel import router as admin_panel_router
from .admin.manage_users import router as manage_users_router
from .admin.manage_orders import router as manage_orders_router
from .admin.manage_cities import router as manage_cities_router
from .admin.manage_categories import router as manage_categories_router
from .customer.create_order import router as create_order_router
from .customer.manage_orders import router as customer_orders_router
from .customer.review import router as review_router
from .executor.create_offers import router as create_offer_router
from .executor.complete_order import router as complete_order_router
from .common.start import router as start_router
from .common.profile import router as profile_router
from .common.switch_role import router as switch_role_router
from .executor.manage_offers import router as manage_offers_router

__all__ = [
    "admin_panel_router", "manage_users_router", "manage_orders_router", "manage_offers_router", "manage_cities_router", "manage_categories_router",
    "create_order_router", "customer_orders_router", "review_router",
    "create_offer_router", "complete_order_router",
    "start_router", "profile_router", "switch_role_router"
]