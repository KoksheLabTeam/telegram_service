from typing import Annotated, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.api.offer import send_telegram_message
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.schemas.offer import OfferRead, OfferUpdate
from app.core.services import order as order_service
from app.core.schemas.order import OrderRead, OrderCreate, OrderUpdate
from app.api.depends.user import get_current_user, get_admin_user
from datetime import datetime, timedelta
import logging
import aiohttp
from app.bot.config import BOT_TOKEN

router = APIRouter(prefix="/order", tags=["Order"])
logger = logging.getLogger(__name__)

@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
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

    # Уведомление исполнителям (всем с подходящей категорией)
    executors = session.query(User).filter(
        User.is_executor == True,
        User.categories.any(id=data.category_id)
    ).all()
    message = (
        f"Новый заказ '{order.title}' (ID: {order.id}):\n"
        f"Категория: {order.category.name}\n"
        f"Желаемая цена: {order.desired_price} тенге\n"
        f"Срок: {order.due_date.strftime('%Y-%m-%d %H:%M')}"
    )
    for executor in executors:
        try:
            await send_telegram_message(executor.telegram_id, message)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления исполнителю {executor.id}: {e}")

    return order

@router.get("/", response_model=List[OrderRead])
def get_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Получить список заказов текущего пользователя."""
    logger.info(f"Получение заказов для пользователя {current_user.id}")
    try:
        orders = order_service.get_orders_by_user(session, current_user.id)
        logger.info(f"Найдено {len(orders)} заказов для пользователя {current_user.id}")
        for order in orders:
            logger.debug(f"Заказ ID {order.id}: status={order.status}, customer_id={order.customer_id}, customer={order.customer}")
        return orders
    except Exception as e:
        logger.error(f"Ошибка в get_orders: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")

@router.get("/available", response_model=List[OrderRead])
def get_available_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    logger.info(f"Запрос доступных заказов от пользователя {current_user.id}")
    if not current_user.is_executor:
        logger.warning(f"Попытка доступа к доступным заказам не исполнителем: {current_user.id}")
        raise HTTPException(status_code=403, detail="Только исполнители могут видеть доступные заказы")
    try:
        orders = order_service.get_available_orders(session)
        logger.info(f"Найдено {len(orders)} доступных заказов: {[order.id for order in orders]}")
        for order in orders:
            logger.debug(f"Заказ ID {order.id}: status={order.status}, customer_id={order.customer_id}, customer={order.customer}")
        return orders
    except Exception as e:
        logger.error(f"Ошибка в get_available_orders: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")

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

    offers = order.offers
    for offer in offers:
        executor = session.get(User, offer.executor_id)
        offer.executor_rating = executor.rating  # Добавляем рейтинг исполнителя
    return offers

@router.patch("/{id}", response_model=OrderRead)
async def update_order(
    id: int,
    data: OrderUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Обновить заказ (доступно только заказчику, или исполнителю для завершения)."""
    logger.info(f"Обновление заказа ID {id} пользователем {current_user.id}")
    order = order_service.get_order_by_id(session, id)
    if order.customer_id != current_user.id and order.executor_id != current_user.id:
        logger.warning(f"Попытка обновления заказа ID {id} без прав: {current_user.id}")
        raise HTTPException(status_code=403, detail="Нет прав для обновления этого заказа")

    if data.status == "Выполнен" and order.executor_id == current_user.id:
        # Завершение заказа исполнителем
        if order.status != "В_прогрессе":
            raise HTTPException(status_code=400, detail="Заказ можно завершить только из статуса 'В_прогрессе'")
        updated_order = order_service.update_order_by_id(session, data, id)
        customer = session.get(User, order.customer_id)
        message = (
            f"Заказ '{order.title}' (ID: {id}) завершён исполнителем.\n"
            f"Пожалуйста, оставьте отзыв."
        )
        try:
            await send_telegram_message(customer.telegram_id, message)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления заказчику {customer.id}: {e}")
        return updated_order
    elif order.customer_id == current_user.id:
        if data.status and data.status not in ["В_ожидании", "Отменен"]:
            raise HTTPException(status_code=403,
                                detail="Заказчик может менять статус только на 'В_ожидании' или 'Отменен'")
        updated_order = order_service.update_order_by_id(session, data, id)
        if data.status == "Отменен" and order.executor_id:
            executor = session.get(User, order.executor_id)
            message = (
                f"Заказ '{order.title}' (ID: {id}) был отменён заказчиком."
            )
            try:
                await send_telegram_message(executor.telegram_id, message)
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления исполнителю {executor.id}: {e}")
        logger.info(f"Заказ ID {id} обновлён")
        return updated_order
    else:
        raise HTTPException(status_code=403, detail="Нет прав для обновления этого заказа")

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Удалить заказ (доступно заказчику только в статусе 'В_ожидании' или администратору)."""
    logger.info(f"Удаление заказа ID {id} пользователем {current_user.id}")
    order = order_service.get_order_by_id(session, id)
    if current_user.is_admin:
        order_service.delete_order_by_id(session, id)
        logger.info(f"Заказ ID {id} удалён администратором {current_user.id}")
    elif order.customer_id == current_user.id:
        if order.status != "В_ожидании":
            logger.warning(f"Попытка удаления заказа ID {id} не в статусе 'В_ожидании': {current_user.id}")
            raise HTTPException(status_code=403, detail="Заказ можно удалить только в статусе 'В_ожидании'")
        order_service.delete_order_by_id(session, id)
        if order.executor_id:
            executor = session.get(User, order.executor_id)
            message = f"Заказ '{order.title}' (ID: {id}) был удалён заказчиком."
            try:
                await send_telegram_message(executor.telegram_id, message)
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления исполнителю {executor.id}: {e}")
        logger.info(f"Заказ ID {id} удалён заказчиком {current_user.id}")
    else:
        logger.warning(f"Попытка удаления заказа ID {id} без прав: {current_user.id}")
        raise HTTPException(status_code=403, detail="Нет прав для удаления этого заказа")

@router.post("/{id}/cancel", response_model=OrderRead)
async def cancel_order(
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
    canceled_order = order_service.update_order_by_id(session, OrderUpdate(status="Отменен"), id)
    if order.executor_id:
        executor = session.get(User, order.executor_id)
        message = f"Заказ '{order.title}' (ID: {id}) был отменён заказчиком в течение 5 минут."
        try:
            await send_telegram_message(executor.telegram_id, message)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления исполнителю {executor.id}: {e}")
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
    if order.status != "В_ожидании":
        raise HTTPException(status_code=400, detail="Нельзя отклонить предложение для заказа не в статусе 'В_ожидании'")

    offer = offer_service.get_offer_by_id(session, offer_id)
    if offer.order_id != id:
        raise HTTPException(status_code=400, detail="Предложение не относится к этому заказу")

    updated_offer = offer_service.update_offer_by_id(session, OfferUpdate(status="rejected"), offer_id)

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