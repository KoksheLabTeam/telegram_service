# app/bot/handlers/executor/manage_offers.py
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.bot.config import ADMIN_TELEGRAM_ID
from ..common.profile import get_main_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "Мои предложения")
async def show_offers(message: Message):
    telegram_id = await get_user_telegram_id(message)
    user = await api_request("GET", "user/me", telegram_id)
    if not user["is_executor"]:
        await message.answer("Только исполнители могут просматривать свои предложения.", reply_markup=get_main_keyboard({"is_executor": False}))
        return
    try:
        offers = await api_request("GET", "offer/", telegram_id)
        if not offers:
            roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": True, "is_customer": user["is_customer"]}
            await message.answer("У вас нет активных предложений.", reply_markup=get_main_keyboard(roles))
            return

        response = "Ваши предложения:\n\n"
        status_map = {"pending": "Ожидает", "accepted": "Принято", "rejected": "Отклонено"}
        for offer in offers:
            status = status_map.get(offer["status"], offer["status"])
            response += (
                f"ID: {offer['id']}\n"
                f"Заказ ID: {offer['order_id']}\n"
                f"Цена: {offer['price']} тенге\n"
                f"Время: {offer['estimated_time']} часов\n"
                f"Статус: {status}\n"
                f"Создано: {offer['created_at'].split('T')[0]}\n\n"
            )
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": True, "is_customer": user["is_customer"]}
        await message.answer(response.strip(), reply_markup=get_main_keyboard(roles))
    except Exception as e:
        logger.error(f"Ошибка в show_offers: {e}")
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": False}
        await message.answer(f"Ошибка загрузки предложений: {e}", reply_markup=get_main_keyboard(roles))