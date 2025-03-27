# app/api/endpoints/orders.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.models.order import Order
from app.core.schemas.order import OrderCreate, OrderRead, OrderUpdate
from app.core.services import order as order_service
from app.api.depends.user import get_current_user
from app.api.offers import send_telegram_message  # Используем функцию из offer.py
from datetime import datetime, timedelta
import logging

router = APIRouter(prefix="/order", tags=["Orders"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
        data: OrderCreate,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Создать новый заказ (доступно только заказчикам или админам)."""
    logger.info(f"Создание заказа пользователем {current_user.id} (admin: {current_user.is_admin})")
    if not current_user.is_customer and not current_user.is_admin:
        logger.warning(f"Попытка создания заказа не заказчиком: {current_user.id}")
        raise HTTPException(status_code=403, detail="Только заказчики или администраторы могут создавать заказы")
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
    """Получить список заказов текущего пользователя (все заказы для админа)."""
    logger.info(f"Получение заказов для пользователя {current_user.id} (admin: {current_user.is_admin})")
    try:
        if current_user.is_admin:
            orders = session.query(Order).all()
        else:
            orders = order_service.get_orders_by_user(session, current_user.id)
        logger.info(f"Найдено {len(orders)} заказов для пользователя {current_user.id}")
        return orders
    except Exception as e:
        logger.error(f"Ошибка в get_orders: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@router.get("/{id}", response_model=OrderRead)
def get_order(
        id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Получить заказ по ID (доступно заказчику, исполнителю или админу)."""
    logger.info(f"Запрос заказа ID {id} от пользователя {current_user.id} (admin: {current_user.is_admin})")
    order = order_service.get_order_by_id(session, id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.customer_id != current_user.id and order.executor_id != current_user.id and not current_user.is_admin:
        logger.warning(f"Попытка доступа к заказу ID {id} без прав: {current_user.id}")
        raise HTTPException(status_code=403, detail="Нет прав для просмотра этого заказа")
    return order


@router.patch("/{id}", response_model=OrderRead)
async def update_order(
        id: int,
        data: OrderUpdate,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Обновить заказ (доступно заказчику, исполнителю для завершения или админу)."""
    logger.info(f"Обновление заказа ID {id} пользователем {current_user.id} (admin: {current_user.is_admin})")
    order = order_service.get_order_by_id(session, id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.customer_id != current_user.id and order.executor_id != current_user.id and not current_user.is_admin:
        logger.warning(f"Попытка обновления заказа ID {id} без прав: {current_user.id}")
        raise HTTPException(status_code=403, detail="Нет прав для обновления этого заказа")

    if current_user.is_admin:
        # Админ может обновить заказ без ограничений
        updated_order = order_service.update_order_by_id(session, data, id)
    elif data.status == "Выполнен" and order.executor_id == current_user.id:
        # Завершение заказа исполнителем
        if order.status != "IN_PROGRESS":
            raise HTTPException(status_code=400, detail="Заказ можно завершить только из статуса 'IN_PROGRESS'")
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
    elif order.customer_id == current_user.id:
        # Заказчик может менять только определённые статусы
        if data.status and data.status not in ["PENDING", "CANCELLED"]:
            raise HTTPException(status_code=403,
                                detail="Заказчик может менять статус только на 'PENDING' или 'CANCELLED'")
        updated_order = order_service.update_order_by_id(session, data, id)
        if data.status == "CANCELLED" and order.executor_id:
            executor = session.get(User, order.executor_id)
            message = f"Заказ '{order.title}' (ID: {id}) был отменён заказчиком."
            try:
                await send_telegram_message(executor.telegram_id, message)
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления исполнителю {executor.id}: {e}")
    else:
        raise HTTPException(status_code=403, detail="Нет прав для обновления этого заказа")

    logger.info(f"Заказ ID {id} обновлён")
    return updated_order


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
        id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
):
    """Удалить заказ (доступно заказчику в статусе 'PENDING' или админу)."""
    logger.info(f"Удаление заказа ID {id} пользователем {current_user.id} (admin: {current_user.is_admin})")
    order = order_service.get_order_by_id(session, id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if current_user.is_admin:
        order_service.delete_order_by_id(session, id)
        logger.info(f"Заказ ID {id} удалён администратором {current_user.id}")
    elif order.customer_id == current_user.id:
        if order.status != "PENDING":
            logger.warning(f"Попытка удаления заказа ID {id} не в статусе 'PENDING': {current_user.id}")
            raise HTTPException(status_code=403, detail="Заказ можно удалить только в статусе 'PENDING'")
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
    """Отменить заказ (доступно заказчику в течение 30 минут после создания или админу)."""
    logger.info(f"Отмена заказа ID {id} пользователем {current_user.id} (admin: {current_user.is_admin})")
    order = order_service.get_order_by_id(session, id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if not current_user.is_admin and order.customer_id != current_user.id:
        logger.warning(f"Попытка отмены заказа ID {id} не заказчиком: {current_user.id}")
        raise HTTPException(status_code=403, detail="Только заказчик или администратор может отменить этот заказ")
    if not current_user.is_admin and datetime.utcnow() > order.created_at + timedelta(minutes=30):
        logger.warning(f"Попытка отмены заказа ID {id} после 30 минут: {current_user.id}")
        raise HTTPException(status_code=400, detail="Заказ можно отменить только в течение 30 минут после создания")
    canceled_order = order_service.update_order_by_id(session, OrderUpdate(status="CANCELLED"), id)
    if order.executor_id:
        executor = session.get(User, order.executor_id)
        message = f"Заказ '{order.title}' (ID: {id}) был отменён."
        try:
            await send_telegram_message(executor.telegram_id, message)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления исполнителю {executor.id}: {e}")
    logger.info(f"Заказ ID {id} отменён")
    return canceled_order

@router.get("/available", response_model=List[OrderRead])
def get_available_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Получить список доступных заказов для исполнителей или админов."""
    logger.info(f"Запрос GET /order/available от пользователя {current_user.id}")
    if not current_user.is_executor and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Доступ только для исполнителей или админов")
    orders = order_service.get_available_orders(
        session,
        executor_id=current_user.id if not current_user.is_admin else None,
        is_admin=current_user.is_admin
    )
    logger.info(f"Найдено {len(orders)} доступных заказов")
    return orders