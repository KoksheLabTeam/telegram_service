from typing import Annotated, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.services import offer as offer_service
from app.core.schemas.offer import OfferRead, OfferCreate, OfferUpdate
from app.api.depends.user import get_current_user

router = APIRouter(prefix="/offer", tags=["Offer"])

@router.post("/", response_model=OfferRead, status_code=status.HTTP_201_CREATED)
def create_offer(
    data: OfferCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Создать новое предложение (только для исполнителей)."""
    if not current_user.is_executor:
        raise HTTPException(status_code=403, detail="Only executors can create offers")
    return offer_service.create_offer(session, data, current_user.id)

@router.get("/", response_model=List[OfferRead])
def get_offers(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Получить список предложений пользователя."""
    return offer_service.get_offers_by_user(session, current_user.id)

@router.get("/{id}", response_model=OfferRead)
def get_offer(
    id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Получить предложение по ID."""
    offer = offer_service.get_offer_by_id(session, id)
    if offer.executor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this offer")
    return offer

@router.patch("/{id}", response_model=OfferRead)
def update_offer(
    id: int,
    data: OfferUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Обновить предложение (только для владельца)."""
    offer = offer_service.get_offer_by_id(session, id)
    if offer.executor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the executor can update this offer")
    return offer_service.update_offer_by_id(session, data, id)