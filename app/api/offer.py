from typing import Annotated, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models import Order
from app.core.models.user import User
from app.core.schemas.order import OrderUpdate, OrderRead
from app.core.services import offer as offer_service
from app.core.services import order as order_service
from app.core.schemas.offer import OfferRead, OfferCreate, OfferUpdate
from app.api.depends.user import get_current_user
import aiohttp
from app.bot.config import BOT_TOKEN
import logging  # Добавлено

router = APIRouter(prefix="/offer", tags=["Offer"])
logger = logging.getLogger(__name__)  # Добавлено


async def send_telegram_message(chat_id: int, text: str):
    """Отправка сообщения через Telegram API."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                raise Exception(f"Ошибка Telegram API: {await response.text()}")

@router.post("/{id}/offers/{offer_id}/accept", response_model=OrderRead)
async def accept_offer(
    id: int,
    offer_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Принять предложение и назначить исполнителя (доступно только заказчику)."""
    order = order_service.get_order_by_id(session, id)
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Только заказчик может принять предложение")
    if order.status != "В_ожидании":  # Проверка на русский статус
        raise HTTPException(status_code=400, detail="Нельзя принять предложение для заказа не в статусе 'В_ожидании'")

    offer = offer_service.get_offer_by_id(session, offer_id)
    if offer.order_id != id:
        raise HTTPException(status_code=400, detail="Предложение не относится к этому заказу")

    order_data = OrderUpdate(executor_id=offer.executor_id, status="В_прогрессе")
    updated_order = order_service.update_order_by_id(session, order_data, id)
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
        logger.error(f"Ошибка отправки уведомления исполнителю: {e}")

    return updated_order


@router.post("/", response_model=OfferRead, status_code=status.HTTP_201_CREATED)
async def create_offer(
        data: OfferCreate,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Создать новое предложение (доступно только исполнителям)."""
    if not current_user.is_executor:
        raise HTTPException(status_code=403, detail="Только исполнители могут создавать предложения")
    offer = offer_service.create_offer(session, data, current_user.id)

    # Получаем заказ и заказчика
    order = session.get(Order, offer.order_id)
    customer = session.get(User, order.customer_id)

    # Отправляем уведомление заказчику
    message = (
        f"Новое предложение по вашему заказу '{order.title}' (ID: {order.id}):\n"
        f"Исполнитель: {current_user.name}\n"
        f"Цена: {offer.price} тенге\n"
        f"Время выполнения: {offer.estimated_time} часов"
    )
    try:
        await send_telegram_message(customer.telegram_id, message)
    except Exception as e:
        # Логируем ошибку, но не прерываем выполнение
        print(f"Ошибка отправки уведомления: {e}")

    return offer


# Остальные эндпоинты остаются без изменений
@router.get("/", response_model=List[OfferRead])
def get_offers(
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Получить список предложений текущего пользователя."""
    return offer_service.get_offers_by_user(session, current_user.id)


@router.get("/{id}", response_model=OfferRead)
def get_offer(
        id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Получить предложение по ID."""
    offer = offer_service.get_offer_by_id(session, id)
    if offer.executor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет прав для просмотра этого предложения")
    return offer


@router.patch("/{id}", response_model=OfferRead)
def update_offer(
        id: int,
        data: OfferUpdate,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Обновить предложение (доступно только исполнителю)."""
    offer = offer_service.get_offer_by_id(session, id)
    if offer.executor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Только исполнитель может обновлять это предложение")
    return offer_service.update_offer_by_id(session, data, id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_offer(
        id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Удалить предложение (доступно только исполнителю)."""
    offer = offer_service.get_offer_by_id(session, id)
    if offer.executor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Только исполнитель может удалить это предложение")
    offer_service.delete_offer_by_id(session, id)

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
    if order.status != "В_ожидании":  # Проверка на русский статус
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