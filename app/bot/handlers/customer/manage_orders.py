from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.bot.config import ADMIN_TELEGRAM_ID
from ..common.profile import get_main_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "Список заказов")
async def show_orders(message: Message):
    telegram_id = await get_user_telegram_id(message)
    user = await api_request("GET", "user/me", telegram_id)
    try:
        is_executor = user["is_executor"]
        is_customer = user["is_customer"]
        is_admin = telegram_id == ADMIN_TELEGRAM_ID
        if is_executor:
            url = "order/available"
            logger.info(f"Запрос для исполнителя: {url}")
            orders = await api_request("GET", url, telegram_id)
            title = "Доступные заказы:"
            executed_orders = await api_request("GET", "order/", telegram_id)
            executed_orders = [o for o in executed_orders if o["executor_id"] == user["id"]]
        else:
            url = "order/"
            logger.info(f"Запрос для заказчика: {url}")
            orders = await api_request("GET", url, telegram_id)
            title = "Ваши заказы:"
            orders = [o for o in orders if o["customer_id"] == user["id"]]
            executed_orders = []

        if not orders and not executed_orders:
            roles = {"is_admin": is_admin, "is_executor": is_executor, "is_customer": is_customer}
            await message.answer(f"{title.split(':')[0]} пока нет.", reply_markup=get_main_keyboard(roles))
            return

        response = f"{title}\n\n"
        status_map = {"В_ожидании": "Ожидает", "В_прогрессе": "В процессе", "Выполнен": "Завершён", "Отменен": "Отменён"}
        for order in orders:
            status = status_map.get(order["status"], order["status"])
            due_date = order["due_date"].split("T")[0]
            response += (
                f"ID: {order['id']}\n"
                f"Название: {order['title']}\n"
                f"Статус: {status}\n"
                f"Желаемая цена: {order['desired_price']} тенге\n"
                f"Срок: {due_date}\n\n"
            )
            if response.strip():
                roles = {"is_admin": is_admin, "is_executor": is_executor, "is_customer": is_customer}
                await message.answer(response.strip(), reply_markup=get_main_keyboard(roles))
                response = ""

        if is_executor and executed_orders:
            response = "Ваши выполненные заказы:\n\n"
            for order in executed_orders:
                status = status_map.get(order["status"], order["status"])
                due_date = order["due_date"].split("T")[0]
                response += (
                    f"ID: {order['id']}\n"
                    f"Название: {order['title']}\n"
                    f"Статус: {status}\n"
                    f"Желаемая цена: {order['desired_price']} тенге\n"
                    f"Срок: {due_date}\n\n"
                )
            roles = {"is_admin": is_admin, "is_executor": is_executor, "is_customer": is_customer}
            await message.answer(response.strip(), reply_markup=get_main_keyboard(roles))
    except Exception as e:
        logger.error(f"Ошибка в show_orders: {e}")
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": False}
        error_msg = f"Ошибка загрузки заказов: {e}"
        if "500" in str(e):
            error_msg += "\nПроблема на сервере. Обратитесь к администратору."
        await message.answer(error_msg, reply_markup=get_main_keyboard(roles))