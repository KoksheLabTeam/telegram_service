from .main import router as customer_main_router
from .orders import router as customer_orders_router
from .offers import router as customer_offers_router
from .reviews import router as customer_reviews_router  # Добавляем новый роутер

customer_routers = [
    customer_main_router,
    customer_orders_router,
    customer_offers_router,
    customer_reviews_router  # Добавляем в список
]