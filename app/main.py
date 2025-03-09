from fastapi import FastAPI
from app.api.routers import routers

app = FastAPI()
app.include_router(routers)