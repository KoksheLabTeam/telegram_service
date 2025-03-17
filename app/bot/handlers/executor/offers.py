from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.common import api_request, get_main_keyboard
from app.bot.config import API_URL
import logging

router = Router()
logger = logging.getLogger(__name__)

class CreateOfferStates(StatesGroup):
    order_id = State()
    price = State()
    estimated_time = State()

async def start_create_offer(message: Message):
    telegram_id = message.from_user.id
    orders = await api_request("GET", f"{API_URL}order/available", telegram_id)
    if not orders:
        await message.answer("Нет доступных заказов.", reply_markup=get_main_keyboard({"is_executor": True}))
        return
    response = "Доступные заказы:\n\n"
    for order in orders:
        response += f"ID: {order['id']} - {order['title']}\n"
    await message.answer(response + "\nВведите ID заказа для создания предложения:")
    await message.bot.get_state(message.from_user.id, message.chat.id).set_state(CreateOfferStates.order_id)