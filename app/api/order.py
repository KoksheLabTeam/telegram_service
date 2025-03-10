from typing import Annotated, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.services import order as order_service
from app.core.schemas.order import OrderRead, OrderCreate, OrderUpdate
from app.api.depends.user import get_current_user, get_admin_user
from datetime import datetime, timedelta

router = APIRouter(prefix="/order", tags=["Order"])

@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    data: OrderCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Создать новый заказ (только для заказчиков)."""
    if not current_user.is_customer:
        raise HTTPException(status_code=403, detail="Only customers can create orders")
    return order_service.create_order(session, data, current_user.id)

@router.get("/", response_model=List[OrderRead])
def get_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Получить список заказов пользователя."""
    return order_service.get_orders_by_user(session, current_user.id)

@router.get("/{id}", response_model=OrderRead)
def get_order(
    id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Получить заказ по ID."""
    order = order_service.get_order_by_id(session, id)
    if order.customer_id != current_user.id and order.executor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    return order

@router.patch("/{id}", response_model=OrderRead)
def update_order(
    id: int,
    data: OrderUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Обновить заказ (только для владельца)."""
    order = order_service.get_order_by_id(session, id)
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the customer can update this order")
    return order_service.update_order_by_id(session, data, id)

# Эндпоинт для удаления заказа админом
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    id: int,
    admin: Annotated[User, Depends(get_admin_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Удалить заказ (только для админа)."""
    order = order_service.get_order_by_id(session, id)
    session.delete(order)
    session.commit()

# Эндпоинт для отмены заказа заказчиком в течение 5 минут
@router.post("/{id}/cancel", response_model=OrderRead)
def cancel_order(
    id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Отменить заказ заказчиком в течение 5 минут после создания."""
    order = order_service.get_order_by_id(session, id)
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the customer can cancel this order")
    if datetime.utcnow() > order.created_at + timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="Order can only be canceled within 5 minutes of creation")
    order.status = "canceled"
    session.commit()
    session.refresh(order)
    return order