from typing import Annotated
from sqlalchemy.orm import Session
from fastapi.exceptions import HTTPException
from fastapi import Depends, Header, status
from app.core.models.user import User
from app.core.database.helper import get_session

ADMIN_TELEGRAM_ID = 123456789  # Замените на ваш Telegram ID

def get_current_user(
    x_telegram_id: Annotated[str, Header()],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    if not x_telegram_id:
        raise HTTPException(status_code=400, detail="x-telegram-id is missing")
    user = session.query(User).filter(User.telegram_id == int(x_telegram_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def get_admin_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.telegram_id != ADMIN_TELEGRAM_ID:
        raise HTTPException(status_code=403, detail="Permission denied")
    return current_user