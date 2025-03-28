# app/api/endpoints/offers.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models import Order
from app.core.models.user import User
from app.core.schemas.order import OrderRead, OrderUpdate
from app.core.schemas.offer import OfferRead, OfferCreate, OfferUpdate
from app.core.services import order as order_service
from app.core.services import offer as offer_service
from app.api.depends.user import get_current_user
from app.bot.config import BOT_TOKEN
import aiohttp
import logging

router = APIRouter(prefix="/order/{order_id}/offers", tags=["Offers"])
logger = logging.getLogger(__name__)

async def send_telegram_message(chat_id: int, text: str):
    """Отправка сообщения через Telegram API."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                raise Exception(f"Ошибка Telegram API: {await response.text()}")


@router.post("/{order_id}/offers/", response_model=OfferRead, status_code=status.HTTP_201_CREATED)
async def create_offer(
        order_id: int,
        data: OfferCreate,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    logger.info(f"Создание предложения для заказа {order_id} пользователем {current_user.id}")
    if not current_user.is_executor:
        raise HTTPException(status_code=403, detail="Только исполнители могут создавать предложения")

    order = order_service.get_order_by_id(session, order_id)
    if not order or order.status != "PENDING":
        raise HTTPException(status_code=404, detail="Заказ не найден или недоступен для предложений")

    offer = offer_service.create_offer(session, data, current_user.id)
    logger.info(f"Предложение создано: ID {offer.id}")

    customer = session.get(User, order.customer_id)
    message = (
        f"Новое предложение для заказа '{order.title}' (ID: {order_id}):\n"
        f"Исполнитель: {current_user.first_name or 'Без имени'}\n"
        f"Цена: {offer.price} тенге\n"
        f"Дата завершения: {offer.due_date.strftime('%Y-%m-%d %H:%M')}"
    )
    try:
        await send_telegram_message(customer.telegram_id, message)
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления заказчику {customer.id}: {e}")

    return offer

@router.get("/", response_model=List[OfferRead])
def get_offers(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Получить список предложений по заказу (доступно заказчику или админу)."""
    logger.info(f"Запрос предложений для заказа {order_id} от пользователя {current_user.id} (admin: {current_user.is_admin})")
    order = order_service.get_order_by_id(session, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.customer_id != current_user.id and not current_user.is_admin:
        logger.warning(f"Попытка доступа к предложениям заказа {order_id} без прав: {current_user.id}")
        raise HTTPException(status_code=403, detail="Только заказчик или администратор может видеть предложения")
    offers = order.offers
    for offer in offers:
        executor = session.get(User, offer.executor_id)
        offer.executor_rating = executor.rating  # Добавляем рейтинг исполнителя
    return offers

@router.post("/{offer_id}/accept", response_model=OrderRead)
async def accept_offer(
    order_id: int,
    offer_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Принять предложение и назначить исполнителя (доступно заказчику или админу)."""
    logger.info(f"Принятие предложения {offer_id} для заказа {order_id} пользователем {current_user.id} (admin: {current_user.is_admin})")
    order = order_service.get_order_by_id(session, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.customer_id != current_user.id and not current_user.is_admin:
        logger.warning(f"Попытка принятия предложения для заказа {order_id} без прав: {current_user.id}")
        raise HTTPException(status_code=403, detail="Только заказчик или администратор может принять предложение")
    if order.status != "PENDING":
        raise HTTPException(status_code=400, detail="Нельзя принять предложение для заказа не в статусе 'PENDING'")
    offer = offer_service.get_offer_by_id(session, offer_id)
    if not offer or offer.order_id != order_id:
        raise HTTPException(status_code=400, detail="Предложение не найдено или не относится к этому заказу")
    order_data = OrderUpdate(executor_id=offer.executor_id, status="IN_PROGRESS")
    updated_order = order_service.update_order_by_id(session, order_data, order_id)
    offer_service.update_offer_by_id(session, OfferUpdate(status="accepted"), offer_id)
    executor = session.get(User, offer.executor_id)
    message = (
        f"Ваше предложение по заказу '{order.title}' (ID: {order.id}) принято!\n"
        f"Цена: {offer.price} тенге\n"
        f"Время выполнения: {offer.estimated_time} часов\n"
        f"Свяжитесь с заказчиком: @{current_user.username}"
    )
    try:
        await send_telegram_message(executor.telegram_id, message)
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления исполнителю {executor.id}: {e}")
    logger.info(f"Предложение {offer_id} принято для заказа {order_id}")
    return updated_order

@router.post("/{offer_id}/reject", response_model=OfferRead)
async def reject_offer(
    order_id: int,
    offer_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Отклонить предложение (доступно заказчику или админу)."""
    logger.info(f"Отклонение предложения {offer_id} для заказа {order_id} пользователем {current_user.id} (admin: {current_user.is_admin})")
    order = order_service.get_order_by_id(session, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.customer_id != current_user.id and not current_user.is_admin:
        logger.warning(f"Попытка отклонения предложения для заказа {order_id} без прав: {current_user.id}")
        raise HTTPException(status_code=403, detail="Только заказчик или администратор может отклонить предложение")
    if order.status != "PENDING":
        raise HTTPException(status_code=400, detail="Нельзя отклонить предложение для заказа не в статусе 'PENDING'")
    offer = offer_service.get_offer_by_id(session, offer_id)
    if not offer or offer.order_id != order_id:
        raise HTTPException(status_code=400, detail="Предложение не найдено или не относится к этому заказу")
    updated_offer = offer_service.update_offer_by_id(session, OfferUpdate(status="rejected"), offer_id)
    executor = session.get(User, offer.executor_id)
    message = (
        f"Ваше предложение по заказу '{order.title}' (ID: {order.id}) было отклонено.\n"
        f"Цена: {offer.price} тенге\n"
        f"Время выполнения: {offer.estimated_time} часов"
    )
    try:
        await send_telegram_message(executor.telegram_id, message)
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления исполнителю {executor.id}: {e}")
    logger.info(f"Предложение {offer_id} отклонено для заказа {order_id}")
    return updated_offer