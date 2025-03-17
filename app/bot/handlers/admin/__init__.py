from .main import router as admin_main_router
from .user_management import router as user_management_router
from .order_management import router as order_management_router
from .city_management import router as city_management_router
from .category_management import router as category_management_router

admin_routers = [
    admin_main_router,
    user_management_router,
    order_management_router,
    city_management_router,
    category_management_router
]