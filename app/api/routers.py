from fastapi import APIRouter
from app.api.user import router as user_router
from app.api.order import router as order_router
from app.api.offer import router as offer_router
from app.api.review import router as review_router

routers = APIRouter(prefix="/api")
routers.include_router(user_router)
routers.include_router(order_router)
routers.include_router(offer_router)
routers.include_router(review_router)