from fastapi import FastAPI
from app.api.routers import routers  # Предполагается, что это ваш роутер
from app.core.models import Base
from app.core.database.helper import engine, SessionLocal
from app.core.models.city import City
from app.core.models.category import Category
from sqlalchemy.orm import Session
import logging

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        if not session.query(City).first():
            default_city = City(name="Кокшетау")
            session.add(default_city)
            session.commit()
            logger.info("Добавлен город по умолчанию: Кокшетау")
        if not session.query(Category).first():
            default_category = Category(name="Общие услуги")
            session.add(default_category)
            session.commit()
            logger.info("Добавлена категория по умолчанию: Общие услуги")

@app.on_event("startup")
async def startup():
    init_db()
    logger.info("API запущен, роутеры подключены")

# Проверяем подключение роутера
logger.info(f"Подключение роутера: {routers}")
app.include_router(routers)

# Для отладки: выводим все маршруты
@app.get("/debug/routes")
async def debug_routes():
    routes = [{"path": route.path, "methods": list(route.methods)} for route in app.routes]
    logger.info(f"Зарегистрированные маршруты: {routes}")
    return routes