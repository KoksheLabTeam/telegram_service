from typing import Annotated, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.services import category as category_service
from app.core.schemas.category import CategoryRead, CategoryCreate
from app.api.depends.user import get_current_user, get_admin_user

router = APIRouter(prefix="/category", tags=["Category"])

@router.get("/", response_model=List[CategoryRead])
def get_categories(session: Annotated[Session, Depends(get_session)]):
    """Получить список всех категорий."""
    return category_service.get_all_categories(session)

@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    admin: Annotated[User, Depends(get_admin_user)],  # Включаем проверку админа
    session: Annotated[Session, Depends(get_session)],
):
    """Создать новую категорию (только для админа)."""
    return category_service.create_category(session, data)

@router.get("/{id}", response_model=CategoryRead)
def get_category(
    id: int,
    session: Annotated[Session, Depends(get_session)],
):
    """Получить категорию по ID."""
    return category_service.get_category_by_id(session, id)

# Эндпоинт для удаления категории админом
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    id: int,
    admin: Annotated[User, Depends(get_admin_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Удалить категорию (только для админа)."""
    category = category_service.get_category_by_id(session, id)
    session.delete(category)
    session.commit()