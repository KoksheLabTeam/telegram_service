from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.bot.config import ADMIN_TELEGRAM_ID, API_URL
from .profile import get_main_keyboard
from .start import ensure_user_exists  # Используем импорт
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "Сменить роль")
async def switch_role(message: Message):
    telegram_id = await get_user_telegram_id(message)
    user = await ensure_user_exists(telegram_id, message)
    if not user:
        return
    try:
        new_roles = {
            "is_customer": not user["is_customer"],
            "is_executor": not user["is_executor"]
        }
        await api_request("PATCH", "user/me", telegram_id, data=new_roles)
        updated_user = await api_request("GET", "user/me", telegram_id)
        roles = {
            "is_admin": telegram_id == ADMIN_TELEGRAM_ID,
            "is_executor": updated_user["is_executor"],
            "is_customer": updated_user["is_customer"]
        }
        role_text = "Заказчик" if updated_user["is_customer"] else "Исполнитель"
        await message.answer(f"Роль успешно изменена на: {role_text}", reply_markup=get_main_keyboard(roles))
    except Exception as e:
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": False}
        await message.answer(f"Ошибка при смене роли: {e}", reply_markup=get_main_keyboard(roles))

@router.callback_query(F.data == "back")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    user = await ensure_user_exists(telegram_id, callback.message)
    if not user:
        return
    is_admin = telegram_id == ADMIN_TELEGRAM_ID
    roles = {"is_admin": is_admin, "is_executor": user["is_executor"], "is_customer": user["is_customer"]}
    await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard(roles))
    await state.clear()
    await callback.answer()