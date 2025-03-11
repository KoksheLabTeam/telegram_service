from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.core.models.order import Order
from app.core.schemas.order import OrderCreate, OrderUpdate
from app.core.services.category import get_category_by_id

def create_order(session: Session, data: OrderCreate, customer_id: int) -> Order:
    get_category_by_id(session, data.category_id)
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

def get_orders_by_user(session: Session, user_id: int) -> list[Order]:
    stmt = select(Order).where((Order.customer_id == user_id) | (Order.executor_id == user_id))
    return session.scalars(stmt).all()

def update_order_by_id(session: Session, data: OrderUpdate, id: int) -> Order:
    order = get_order_by_id(session, id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)
    try:
        session.commit()
        session.refresh(order)
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update order: {e}")
    return order

def delete_order_by_id(session: Session, id: int):
    order = get_order_by_id(session, id)
    session.delete(order)
    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete order: {e}")