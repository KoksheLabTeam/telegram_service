from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.bot.config import ADMIN_TELEGRAM_ID, API_URL
from ..common.profile import get_main_keyboard

router = Router()

class AdminPanel(StatesGroup):
    delete_order = State()

@router.callback_query(F.data == "list_orders")
async def list_orders(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    try:
        orders = await api_request("GET", "order/", telegram_id)
        if not orders:
            await callback.message.answer("Заказов нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return
        response = "Список заказов:\n\n"
        status_map = {
            "В_ожидании": "Ожидает",
            "В_прогрессе": "В процессе",
            "Выполнен": "Завершён",
            "Отменен": "Отменён"
        }
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
        await callback.message.answer(response.strip(), reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        await callback.message.answer(f"Ошибка загрузки заказов: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.callback_query(F.data == "delete_order")
async def start_delete_order(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID заказа для удаления:")
    await state.set_state(AdminPanel.delete_order)
    await callback.answer()

@router.message(AdminPanel.delete_order)
async def process_delete_order(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    try:
        order_id = int(message.text)
        await api_request("DELETE", f"order/{order_id}", telegram_id)
        await message.answer(f"Заказ с ID {order_id} удалён.", reply_markup=get_main_keyboard({"is_admin": True}))
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID.", reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        await message.answer(f"Ошибка удаления заказа: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()