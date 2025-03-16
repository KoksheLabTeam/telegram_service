from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.routers import routers
from app.core.models import Base
from app.core.database.helper import engine, SessionLocal
from app.core.models.city import City
from app.core.models.category import Category
from sqlalchemy.orm import Session
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Функция инициализации базы данных
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

# Lifespan handler для управления событиями жизненного цикла
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, выполняемый при запуске приложения
    logger.info("Инициализация приложения...")
    init_db()  # Инициализация базы данных
    logger.info("API запущен, роутеры подключены")
    yield  # Здесь приложение продолжает работу
    # Код, выполняемый при завершении работы приложения (если нужен)
    logger.info("Завершение работы приложения...")

# Создание экземпляра FastAPI с lifespan
app = FastAPI(lifespan=lifespan)

# Подключение роутера
logger.info(f"Подключение роутера: {routers}")
app.include_router(routers)

# Для отладки: выводим все маршруты
@app.get("/debug/routes")
async def debug_routes():
    routes = [{"path": route.path, "methods": list(route.methods)} for route in app.routes]
    logger.info(f"Зарегистрированные маршруты: {routes}")
    return routes