from typing import Annotated, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.services import city as city_service
from app.core.schemas.city import CityRead, CityCreate
from app.api.depends.user import get_current_user, get_admin_user

router = APIRouter(prefix="/city", tags=["City"])

@router.get("/", response_model=List[CityRead])
def get_cities(session: Annotated[Session, Depends(get_session)]):
    """Получить список всех городов."""
    return city_service.get_all_cities(session)

@router.post("/", response_model=CityRead, status_code=status.HTTP_201_CREATED)
def create_city(
    data: CityCreate,
    admin: Annotated[User, Depends(get_admin_user)],  # Включаем проверку админа или отключаем
    session: Annotated[Session, Depends(get_session)],
):
    """Создать новый город (только для админа)."""
    return city_service.create_city(session, data)

@router.get("/{id}", response_model=CityRead)
def get_city(
    id: int,
    session: Annotated[Session, Depends(get_session)],
):
    """Получить город по ID."""
    return city_service.get_city_by_id(session, id)

# Эндпоинт для удаления города админом
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_city(
    id: int,
    admin: Annotated[User, Depends(get_admin_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Удалить город (только для админа)."""
    city = city_service.get_city_by_id(session, id)
    session.delete(city)
    session.commit()