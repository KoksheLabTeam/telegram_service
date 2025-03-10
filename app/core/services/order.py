from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.core.models.order import Order
from app.core.schemas.order import OrderCreate, OrderUpdate
from app.core.services.category import get_category_by_id  # Импортируем для проверки

def create_order(session: Session, data: OrderCreate, customer_id: int) -> Order:
    # Проверяем, существует ли категория
    get_category_by_id(session, data.category_id)  # Вызовет 404, если категория не найдена
    order_data = data.model_dump()
    order = Order(**order_data, customer_id=customer_id)
    session.add(order)
    try:
        session.commit()
        session.refresh(order)
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create order: {e}")
    return order

def get_order_by_id(session: Session, id: int) -> Order:
    order = session.get(Order, id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

def update_order_by_id(session: Session, data: OrderUpdate, id: int) -> Order:
    order = get_order_by_id(session, id)
    update_data = data.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(order, key, value)
    try:
        session.commit()
        session.refresh(order)
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update order: {e}")
    return order