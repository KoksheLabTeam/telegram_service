from aiogram import Router, F
from aiogram.types import Message
from app.bot.handlers.common import get_main_keyboard, get_user_roles
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "Создать заказ")
async def create_order_entrypoint(message: Message):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer("Только заказчики могут создавать заказы.", reply_markup=get_main_keyboard(roles))
        return
    # Передаем управление в orders.py
    from .orders import start_create_order
    await start_create_order(message)