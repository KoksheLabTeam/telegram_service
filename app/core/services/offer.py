from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.core.models.offer import Offer
from app.core.models.order import Order
from app.core.models.user import User  # Добавлено
from app.core.schemas.offer import OfferCreate, OfferUpdate

def create_offer(session: Session, data: OfferCreate, executor_id: int) -> Offer:
    """Создать новое предложение."""
    order = session.get(Order, data.order_id)
    if not order:
        raise HTTPException(status_code=400, detail="Заказ не найден")
    executor = session.get(User, executor_id)
    if order.customer_id == executor_id and not executor.is_admin:
        raise HTTPException(status_code=400, detail="Самопредложение запрещено для не-администраторов")
    offer_data = data.model_dump()
    offer = Offer(**offer_data, executor_id=executor_id)
    session.add(offer)
    try:
        session.commit()
        session.refresh(offer)
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при создании предложения: {e}")
    return offer

def get_offer_by_id(session: Session, id: int) -> Offer:
    """Получить предложение по ID."""
    offer = session.get(Offer, id)
    if not offer:
        raise HTTPException(status_code=404, detail="Предложение не найдено")
    return offer

def get_offers_by_user(session: Session, user_id: int) -> list[Offer]:
    """Получить список предложений пользователя."""
    stmt = select(Offer).where(Offer.executor_id == user_id)
    return session.scalars(stmt).all()

def update_offer_by_id(session: Session, data: OfferUpdate, id: int) -> Offer:
    """Обновить данные предложения по ID."""
    offer = get_offer_by_id(session, id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(offer, key, value)
    try:
        session.commit()
        session.refresh(offer)
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении предложения: {e}")
    return offer

def delete_offer_by_id(session: Session, id: int):
    """Удалить предложение по ID."""
    offer = get_offer_by_id(session, id)
    session.delete(offer)
    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении предложения: {e}")