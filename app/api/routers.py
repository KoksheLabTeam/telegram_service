from fastapi import APIRouter
from app.api.user import router as user_router
from app.api.review import router as review_router
from app.api.city import router as city_router
from app.api.category import router as category_router
from app.api.orders import router as orders_router
from app.api.offers import router as offers_router  # Добавляем роутер предложений

routers = APIRouter(prefix="/api")
routers.include_router(user_router)
routers.include_router(review_router)
routers.include_router(city_router)
routers.include_router(category_router)
routers.include_router(orders_router)
routers.include_router(offers_router)  # Подключаем роутер предложений