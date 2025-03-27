from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from app.core.models.order import Order, OrderStatus
from app.core.schemas.order import OrderCreate, OrderUpdate
from app.core.services.category import get_category_by_id
from app.core.models.user import User

def create_order(session: Session, data: OrderCreate, customer_id: int) -> Order:
    """Создать новый заказ."""
    get_category_by_id(session, data.category_id)  # Проверка существования категории
    order_data = data.model_dump()
    order = Order(**order_data, customer_id=customer_id)
    session.add(order)
    try:
        session.commit()
        session.refresh(order)
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при создании заказа: {e}")
    return order

def get_order_by_id(session: Session, id: int) -> Order:
    """Получить заказ по ID."""
    order = session.get(Order, id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order

def get_orders_by_user(session: Session, user_id: int) -> list[Order]:
    """Получить список заказов пользователя."""
    stmt = select(Order).where((Order.customer_id == user_id) | (Order.executor_id == user_id))
    return session.scalars(stmt).all()

class OrderService:
    def get_available_orders(self, session: Session, executor_id: int = None, is_admin: bool = False):
        query = session.query(Order).filter(Order.status == "PENDING")
        if executor_id and not is_admin:
            query = (
                query
                .join(User, Order.customer_id == User.id)
                .filter(Order.customer_id != executor_id)
            )
        return query.all()

order_service = OrderService()

def update_order_by_id(session: Session, data: OrderUpdate, id: int) -> Order:
    """Обновить данные заказа по ID."""
    order = get_order_by_id(session, id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)
    try:
        session.commit()
        session.refresh(order)
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении заказа: {e}")
    return order

def delete_order_by_id(session: Session, id: int):
    """Удалить заказ по ID."""
    order = get_order_by_id(session, id)
    session.delete(order)
    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении заказа: {e}")