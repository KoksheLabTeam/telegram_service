from typing import Annotated
from sqlalchemy.orm import Session
from fastapi.exceptions import HTTPException
from fastapi import Depends, Header, status
from app.core.models.user import User
from app.core.database.helper import get_session
from app.bot.config import ADMIN_TELEGRAM_ID

def get_current_user(
    x_telegram_id: Annotated[str, Header()],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    if not x_telegram_id:
        raise HTTPException(status_code=400, detail="Заголовок x-telegram-id отсутствует")
    telegram_id = int(x_telegram_id)  # Безопасно для больших чисел в Python
    user = session.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

def get_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Проверить, является ли текущий пользователь администратором."""
    if current_user.telegram_id != ADMIN_TELEGRAM_ID:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    return current_user