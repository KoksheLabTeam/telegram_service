from aiogram import Router, F
from aiogram.types import Message
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.bot.config import ADMIN_TELEGRAM_ID
from ..common.profile import get_main_keyboard

router = Router()

@router.message(F.text == "Оставить отзыв")
async def start_review(message: Message):
    telegram_id = await get_user_telegram_id(message)
    user = await api_request("GET", "user/me", telegram_id)
    if not user["is_customer"]:
        await message.answer("Только заказчики могут оставлять отзывы.", reply_markup=get_main_keyboard({"is_customer": False}))
        return
    await message.answer("Функция оставления отзыва пока в разработке.")
    # Здесь можно добавить FSM для сбора данных отзыва (order_id, rating, comment)