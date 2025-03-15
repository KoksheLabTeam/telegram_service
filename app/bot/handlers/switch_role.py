from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.bot.config import API_URL
from app.bot.handlers.utils import api_request, get_user_telegram_id

router = Router()

def get_main_keyboard():
    from .start import get_main_keyboard
    return get_main_keyboard()

@router.message(F.text == "Сменить роль")
async def switch_role(message: Message):
    telegram_id = get_user_telegram_id(message)
    try:
        user = await api_request("GET", f"{API_URL}user/me", telegram_id)
        current_role = "Заказчик" if user["is_customer"] else "Исполнитель" if user["is_executor"] else "Не определена"
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
    try:
        # Обновляем роль через PATCH
        update_data = {
            "is_customer": role == "customer",
            "is_executor": role == "executor"
        }
        await api_request("PATCH", f"{API_URL}user/me", telegram_id, data=update_data)
        await callback.message.answer(f"Роль успешно изменена на: {role_name}", reply_markup=get_main_keyboard())
    except Exception as e:
        await callback.message.answer(f"Ошибка смены роли: {e}", reply_markup=get_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back")
async def back_to_main(callback: CallbackQuery):
    is_admin = callback.from_user.id == ADMIN_TELEGRAM_ID
    await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard(is_admin))
    await callback.answer()