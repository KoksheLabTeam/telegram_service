from typing import Annotated, List
from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.services import user as user_service
from app.core.schemas.user import UserRead, UserCreate, UserUpdate
from app.api.depends.user import get_current_user, get_admin_user
from fastapi.exceptions import HTTPException

router = APIRouter(prefix="/user", tags=["User"])

@router.get("/me", response_model=UserRead)
def get_me(user: Annotated[User, Depends(get_current_user)]):
    return user

@router.get("/all", response_model=List[UserRead])
def get_all_users(
    admin: Annotated[User, Depends(get_admin_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Получить список всех пользователей (только для админа)."""
    return session.query(User).all()

@router.post("/", response_model=UserRead)
def create_user(
    data: UserCreate,
    session: Annotated[Session, Depends(get_session)],
):
    return user_service.create_user(session, data)

@router.patch("/me", response_model=UserRead)
def update_me(
    data: UserUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    if data.is_customer is not None or data.is_executor is not None:
        raise HTTPException(status_code=403, detail="Role change only through admin")
    return user_service.update_user_by_id(session, data, user.id)

@router.patch("/{id}", response_model=UserRead)
def update_user_by_id(
    id: int,
    data: UserUpdate,
    admin: Annotated[User, Depends(get_admin_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return user_service.update_user_by_id(session, data, id)