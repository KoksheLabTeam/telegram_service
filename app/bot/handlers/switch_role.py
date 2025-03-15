from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.core.services.user import get_user_by_id, update_user_by_id
from app.core.schemas.user import UserUpdate
from app.core.models.user import User  # Добавлен импорт
from app.bot.config import ADMIN_TELEGRAM_ID
from app.bot.handlers.utils import get_db_session, get_user_telegram_id
from .start import get_main_keyboard

router = Router()

@router.message(F.text == "Сменить роль")
async def switch_role(message: Message):
    telegram_id = get_user_telegram_id(message)
    session = next(get_db_session())
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await message.answer("Пользователь не найден. Используйте /start для регистрации.", reply_markup=get_main_keyboard())
            return
        current_role = "Заказчик" if user.is_customer else "Исполнитель" if user.is_executor else "Не определена"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Заказчик", callback_data="role_customer")],
            [InlineKeyboardButton(text="Исполнитель", callback_data="role_executor")],
            [InlineKeyboardButton(text="Назад", callback_data="back")]
        ])
        await message.answer(f"Текущая роль: {current_role}\nВыберите новую роль:", reply_markup=keyboard)
    except Exception as e:
        await message.answer(f"Ошибка загрузки текущей роли: {e}", reply_markup=get_main_keyboard())

@router.callback_query(F.data.startswith("role_"))
async def change_role(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    role = callback.data.split("_")[1]
    role_name = "Заказчик" if role == "customer" else "Исполнитель"
    session = next(get_db_session())
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await callback.message.answer("Пользователь не найден.", reply_markup=get_main_keyboard())
            return
        update_data = UserUpdate(
            is_customer=role == "customer",
            is_executor=role == "executor"
        )
        updated_user = update_user_by_id(session, update_data, user.id)
        roles = {
            "is_admin": telegram_id == ADMIN_TELEGRAM_ID,
            "is_executor": updated_user.is_executor,
            "is_customer": updated_user.is_customer
        }
        await callback.message.answer(f"Роль успешно изменена на: {role_name}", reply_markup=get_main_keyboard(roles))
    except Exception as e:
        await callback.message.answer(f"Ошибка смены роли: {e}", reply_markup=get_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back")
async def back_to_main(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    session = next(get_db_session())
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        roles = {
            "is_admin": telegram_id == ADMIN_TELEGRAM_ID,
            "is_executor": user.is_executor if user else False,
            "is_customer": user.is_customer if user else False
        }
    except Exception:
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": False}
    await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard(roles))
    await callback.answer()