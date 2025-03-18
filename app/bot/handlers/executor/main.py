from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL
import logging

from app.bot.handlers.executor.offers import start_create_offer

router = Router()
logger = logging.getLogger(__name__)

class CompleteOrderStates(StatesGroup):
    select_order = State()

@router.message(F.text == "Создать предложение")
async def create_offer_entrypoint(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles.get("is_executor"):
        await message.answer(
            "Эта функция доступна только для исполнителей.",
            reply_markup=get_main_keyboard(roles)
        )
        return
    try:
        await start_create_offer(message, state)
    except Exception as e:
        logger.error(f"Ошибка при создании предложения: {e}")
        await message.answer(
            f"Не удалось начать создание предложения: {e}",
            reply_markup=get_main_keyboard(roles)
        )

@router.message(F.text == "Список заказов")
async def list_orders(message: Message):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        if not orders:
            await message.answer("У вас нет заказов.", reply_markup=get_main_keyboard(roles))
            return
        response = "Ваши заказы:\n\n"
        for order in orders:
            status = {"В_ожидании": "Ожидает", "В_прогрессе": "В процессе", "Выполнен": "Завершён", "Отменен": "Отменён"}.get(order["status"], order["status"])
            response += f"ID: {order['id']} - {order['title']} ({status})\n"
        await message.answer(response, reply_markup=get_main_keyboard(roles))
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

@router.message(F.text == "Завершить заказ")
async def complete_order_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_executor"]:
        await message.answer("Только исполнители могут завершать заказы.", reply_markup=get_main_keyboard(roles))
        return
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        active_orders = [o for o in orders if o["status"] == "В_прогрессе" and o["executor_id"] == telegram_id]
        if not active_orders:
            await message.answer("У вас нет активных заказов для завершения.", reply_markup=get_main_keyboard(roles))
            return
        response = "Ваши активные заказы:\n\n"
        for order in active_orders:
            response += f"ID: {order['id']} - {order['title']}\n"
        await message.answer(response + "\nВведите ID заказа для завершения:")
        await state.set_state(CompleteOrderStates.select_order)
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

@router.message(CompleteOrderStates.select_order)
async def complete_order_process(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        order_id = int(message.text.strip())
        order_data = {"status": "Выполнен"}
        await api_request("PATCH", f"{API_URL}order/{order_id}", telegram_id, data=order_data)
        await message.answer(f"Заказ ID {order_id} завершён!", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()
    except ValueError:
        await message.answer("Ошибка: Введите корректный ID заказа")
    except Exception as e:
        logger.error(f"Ошибка завершения заказа: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()