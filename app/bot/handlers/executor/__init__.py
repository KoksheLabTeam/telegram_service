from .main import router as executor_main_router
from .offers import router as executor_offers_router

executor_routers = [
    executor_main_router,
    executor_offers_router
]