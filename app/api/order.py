from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.services import order as order_service
from app.core.schemas.order import OrderRead, OrderCreate, OrderUpdate
from app.api.depends.user import get_current_user, get_admin_user

router = APIRouter(prefix="/order", tags=["Order"])

@router.post("/", response_model=OrderRead)
def create_order(
    data: OrderCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    if not user.is_customer:
        raise HTTPException(status_code=403, detail="Only customers can create orders")
    return order_service.create_order(session, data, user.id)

@router.get("/{id}", response_model=OrderRead)
def get_order(
    id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    order = order_service.get_order_by_id(session, id)
    if order.customer_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return order

@router.patch("/{id}", response_model=OrderRead)
def update_order(
    id: int,
    data: OrderUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    order = order_service.get_order_by_id(session, id)
    if order.customer_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return order_service.update_order_by_id(session, data, id)