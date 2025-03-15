from typing import Annotated, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.services import category as category_service
from app.core.schemas.category import CategoryRead, CategoryCreate, CategoryUpdate
from app.api.depends.user import get_current_user, get_admin_user

router = APIRouter(prefix="/category", tags=["Category"])  # Маршруты для категорий

@router.get("/", response_model=List[CategoryRead])
def get_categories(session: Annotated[Session, Depends(get_session)]):
    """Получить список всех категорий."""
    return category_service.get_all_categories(session)

@router.get("/{id}", response_model=CategoryRead)
def get_category(
    id: int,
    session: Annotated[Session, Depends(get_session)],
):
    """Получить категорию по ID."""
    return category_service.get_category_by_id(session, id)

@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    admin: Annotated[User, Depends(get_admin_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Создать новую категорию (доступно только администратору)."""
    return category_service.create_category(session, data)

@router.patch("/{id}", response_model=CategoryRead)
def update_category(
    id: int,
    data: CategoryUpdate,
    admin: Annotated[User, Depends(get_admin_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Обновить данные категории (доступно только администратору)."""
    return category_service.update_category_by_id(session, data, id)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    id: int,
    admin: Annotated[User, Depends(get_admin_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Удалить категорию (доступно только администратору)."""
    category_service.delete_category_by_id(session, id)