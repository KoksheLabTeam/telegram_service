from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command  # Исправлено: импорт Command из filters
from app.bot.config import ADMIN_TELEGRAM_ID
from app.bot.handlers.utils import api_request, get_user_telegram_id
from .profile import get_main_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)

async def ensure_user_exists(telegram_id: int, message: Message) -> dict:
    try:
        user = await api_request("GET", "user/me", telegram_id)
        return user
    except Exception as e:
        if "404" in str(e):
            try:
                cities = await api_request("GET", "city/", telegram_id)
                if not cities:
                    await message.answer("В системе нет городов. Обратитесь к администратору.")
                    return None
                default_city_id = cities[0]["id"]
                user_data = {
                    "telegram_id": telegram_id,
                    "name": message.from_user.full_name or "Без имени",
                    "username": message.from_user.username,
                    "is_customer": True,  # По умолчанию заказчик
                    "is_executor": False,
                    "city_id": default_city_id
                }
                user = await api_request("POST", "user/", telegram_id, data=user_data)
                return user
            except Exception as e:
                await message.answer(f"Ошибка при создании пользователя: {e}")
                return None
        else:
            await message.answer(f"Ошибка проверки пользователя: {e}")
            return None

@router.message(Command("start"))  # Исправлено: использование фильтра Command
async def start_command(message: Message):
    telegram_id = await get_user_telegram_id(message)
    user = await ensure_user_exists(telegram_id, message)
    if not user:
        return
    is_admin = telegram_id == ADMIN_TELEGRAM_ID
    roles = {"is_admin": is_admin, "is_executor": user["is_executor"], "is_customer": user["is_customer"]}
    await message.answer("Добро пожаловать!", reply_markup=get_main_keyboard(roles))