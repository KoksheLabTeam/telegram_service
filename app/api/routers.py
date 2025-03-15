from fastapi import APIRouter
from app.api.user import router as user_router
from app.api.offer import router as offer_router
from app.api.review import router as review_router
from app.api.city import router as city_router
from app.api.category import router as category_router
from app.api.order import router as order_router

routers = APIRouter(prefix="/api")
routers.include_router(user_router)
routers.include_router(order_router)  # Убедитесь, что эта строка присутствует
routers.include_router(offer_router)
routers.include_router(review_router)
routers.include_router(city_router)
routers.include_router(category_router)