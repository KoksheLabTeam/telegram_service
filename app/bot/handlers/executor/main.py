from aiogram import Router, F
from aiogram.types import Message
from app.bot.handlers.common import get_main_keyboard, get_user_roles
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "Создать предложение")
async def create_offer_entrypoint(message: Message):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_executor"]:
        await message.answer("Только исполнители могут создавать предложения.", reply_markup=get_main_keyboard(roles))
        return
    # Передаем управление в offers.py
    from .offers import start_create_offer
    await start_create_offer(message)