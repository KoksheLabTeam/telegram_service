from typing import Annotated, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.services import user as user_service
from app.core.schemas.user import UserRead, UserCreate, UserUpdate
from app.api.depends.user import get_current_user, get_admin_user
from fastapi.exceptions import HTTPException

router = APIRouter(prefix="/user", tags=["User"])  # Маршруты для пользователей

@router.get("/by_telegram_id/{telegram_id}", response_model=UserRead)
def get_user_by_telegram_id(
    telegram_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Получить пользователя по Telegram ID."""
    user = session.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

@router.get("/me", response_model=UserRead)
def get_me(user: Annotated[User, Depends(get_current_user)]):
    """Получить данные текущего пользователя."""
    return user

@router.get("/all", response_model=List[UserRead])
def get_all_users(
    admin: Annotated[User, Depends(get_admin_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Получить список всех пользователей (доступно только администратору)."""
    return user_service.get_users(session)

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    session: Annotated[Session, Depends(get_session)],
):
    """Создать нового пользователя."""
    return user_service.create_user(session, data)

@router.patch("/me", response_model=UserRead)
def update_me(
    data: UserUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Обновить данные текущего пользователя."""
    return user_service.update_user_by_id(session, data, user.id)

@router.patch("/{id}", response_model=UserRead)
def update_user_by_id(
    id: int,
    data: UserUpdate,
    admin: Annotated[User, Depends(get_admin_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Обновить данные пользователя по ID (доступно только администратору)."""
    return user_service.update_user_by_id(session, data, id)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    id: int,
    admin: Annotated[User, Depends(get_admin_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Удалить пользователя по ID (доступно только администратору)."""
    user_service.delete_user_by_id(session, id)