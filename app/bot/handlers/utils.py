from sqlalchemy.orm import Session
from app.core.database.helper import SessionLocal
from aiogram.types import Message
import logging

logger = logging.getLogger(__name__)

def get_db_session() -> Session:
    with SessionLocal() as session:
        yield session

def get_user_telegram_id(message: Message) -> int:
    return message.from_user.id