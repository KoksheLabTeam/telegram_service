from fastapi import FastAPI
from app.api.routers import routers
from app.core.models import Base  # Импортируем Base, чтобы все модели зарегистрировались

app = FastAPI()
app.include_router(routers)