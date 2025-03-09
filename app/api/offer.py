from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.services import offer as offer_service
from app.core.schemas.offer import OfferRead, OfferCreate, OfferUpdate
from app.api.depends.user import get_current_user

router = APIRouter(prefix="/offer", tags=["Offer"])

@router.post("/", response_model=OfferRead)
def create_offer(
    data: OfferCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    if not user.is_executor:
        raise HTTPException(status_code=403, detail="Only executors can create offers")
    return offer_service.create_offer(session, data, user.id)

@router.get("/{id}", response_model=OfferRead)
def get_offer(
    id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    offer = offer_service.get_offer_by_id(session, id)
    order = session.get(Order, offer.order_id)
    if offer.executor_id != user.id and order.customer_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return offer

@router.patch("/{id}", response_model=OfferRead)
def update_offer(
    id: int,
    data: OfferUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    offer = offer_service.get_offer_by_id(session, id)
    order = session.get(Order, offer.order_id)
    if order.customer_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Only customer or admin can update offer status")
    return offer_service.update_offer_by_id(session, data, id)