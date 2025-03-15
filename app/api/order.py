from typing import Annotated, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.schemas.offer import OfferRead, OfferUpdate
from app.core.services import order as order_service
from app.core.schemas.order import OrderRead, OrderCreate, OrderUpdate
from app.api.depends.user import get_current_user, get_admin_user
from datetime import datetime, timedelta
import logging

router = APIRouter(prefix="/order", tags=["Order"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
        data: OrderCreate,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Создать новый заказ (доступно только заказчикам)."""
    logger.info(f"Создание заказа пользователем {current_user.id}")
    if not current_user.is_customer:
        logger.warning(f"Попытка создания заказа не заказчиком: {current_user.id}")
        raise HTTPException(status_code=403, detail="Только заказчики могут создавать заказы")
    order = order_service.create_order(session, data, current_user.id)
    logger.info(f"Заказ создан: ID {order.id}")
    return order


@router.get("/", response_model=List[OrderRead])
def get_orders(
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Получить список заказов текущего пользователя."""
    logger.info(f"Получение заказов для пользователя {current_user.id}")
    orders = order_service.get_orders_by_user(session, current_user.id)
    logger.info(f"Найдено {len(orders)} заказов для пользователя {current_user.id}")
    return orders


@router.get("/available", response_model=List[OrderRead])
def get_available_orders(
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    logger.info(f"Запрос доступных заказов от пользователя {current_user.id}")
    if not current_user.is_executor:
        logger.warning(f"Попытка доступа к доступным заказам не исполнителем: {current_user.id}")
        raise HTTPException(status_code=403, detail="Только исполнители могут видеть доступные заказы")
    orders = order_service.get_available_orders(session)
    logger.info(f"Найдено {len(orders)} доступных заказов")
    return orders


@router.get("/{id}", response_model=OrderRead)
def get_order(
        id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Получить заказ по ID."""
    logger.info(f"Запрос заказа ID {id} от пользователя {current_user.id}")
    order = order_service.get_order_by_id(session, id)
    if order.customer_id != current_user.id and order.executor_id != current_user.id:
        logger.warning(f"Попытка доступа к заказу ID {id} без прав: {current_user.id}")
        raise HTTPException(status_code=403, detail="Нет прав для просмотра этого заказа")
    return order


@router.get("/{id}/offers", response_model=List[OfferRead])
def get_order_offers(
    id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Получить список предложений по заказу (доступно только заказчику)."""
    order = order_service.get_order_by_id(session, id)
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Только заказчик может видеть предложения по этому заказу")

    # Добавляем информацию об исполнителе
    offers = order.offers
    for offer in offers:
        executor = session.get(User, offer.executor_id)
        offer.executor_rating = executor.rating  # Добавляем рейтинг исполнителя
    return offers


@router.patch("/{id}", response_model=OrderRead)
def update_order(
        id: int,
        data: OrderUpdate,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Обновить заказ (доступно только заказчику)."""
    logger.info(f"Обновление заказа ID {id} пользователем {current_user.id}")
    order = order_service.get_order_by_id(session, id)
    if order.customer_id != current_user.id:
        logger.warning(f"Попытка обновления заказа ID {id} не заказчиком: {current_user.id}")
        raise HTTPException(status_code=403, detail="Только заказчик может обновлять этот заказ")
    updated_order = order_service.update_order_by_id(session, data, id)
    logger.info(f"Заказ ID {id} обновлён")
    return updated_order


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
        id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Удалить заказ (доступно заказчику только в статусе 'pending' или администратору)."""
    logger.info(f"Удаление заказа ID {id} пользователем {current_user.id}")
    order = order_service.get_order_by_id(session, id)
    if current_user.is_admin:
        order_service.delete_order_by_id(session, id)
        logger.info(f"Заказ ID {id} удалён администратором {current_user.id}")
    elif order.customer_id == current_user.id:
        if order.status != "pending":
            logger.warning(f"Попытка удаления заказа ID {id} не в статусе 'pending': {current_user.id}")
            raise HTTPException(status_code=403, detail="Заказ можно удалить только в статусе 'pending'")
        order_service.delete_order_by_id(session, id)
        logger.info(f"Заказ ID {id} удалён заказчиком {current_user.id}")
    else:
        logger.warning(f"Попытка удаления заказа ID {id} без прав: {current_user.id}")
        raise HTTPException(status_code=403, detail="Нет прав для удаления этого заказа")


@router.post("/{id}/cancel", response_model=OrderRead)
def cancel_order(
        id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Отменить заказ (доступно заказчику в течение 5 минут после создания)."""
    logger.info(f"Отмена заказа ID {id} пользователем {current_user.id}")
    order = order_service.get_order_by_id(session, id)
    if order.customer_id != current_user.id:
        logger.warning(f"Попытка отмены заказа ID {id} не заказчиком: {current_user.id}")
        raise HTTPException(status_code=403, detail="Только заказчик может отменить этот заказ")
    if datetime.utcnow() > order.created_at + timedelta(minutes=5):
        logger.warning(f"Попытка отмены заказа ID {id} после 5 минут: {current_user.id}")
        raise HTTPException(status_code=400, detail="Заказ можно отменить только в течение 5 минут после создания")
    canceled_order = order_service.update_order_by_id(session, OrderUpdate(status="canceled"), id)
    logger.info(f"Заказ ID {id} отменён")
    return canceled_order

@router.post("/{id}/offers/{offer_id}/reject", response_model=OfferRead)
async def reject_offer(
    id: int,
    offer_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Отклонить предложение (доступно только заказчику)."""
    order = order_service.get_order_by_id(session, id)
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Только заказчик может отклонить предложение")
    if order.status != "pending":
        raise HTTPException(status_code=400, detail="Нельзя отклонить предложение для заказа не в статусе 'pending'")

    offer = offer_service.get_offer_by_id(session, offer_id)
    if offer.order_id != id:
        raise HTTPException(status_code=400, detail="Предложение не относится к этому заказу")

    # Обновляем статус предложения
    updated_offer = offer_service.update_offer_by_id(session, OfferUpdate(status="rejected"), offer_id)

    # Уведомляем исполнителя
    executor = session.get(User, offer.executor_id)
    message = (
        f"Ваше предложение по заказу '{order.title}' (ID: {order.id}) было отклонено заказчиком.\n"
        f"Цена: {offer.price} тенге\n"
        f"Время выполнения: {offer.estimated_time} часов"
    )
    try:
        await send_telegram_message(executor.telegram_id, message)
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления исполнителю: {e}")

    return updated_offer