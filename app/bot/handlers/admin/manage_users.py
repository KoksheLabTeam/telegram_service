from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.bot.config import ADMIN_TELEGRAM_ID, API_URL
from ..common.profile import get_main_keyboard

router = Router()

class AdminPanel(StatesGroup):
    delete_user = State()

@router.callback_query(F.data == "list_users")
async def list_users(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    try:
        users = await api_request("GET", "user/all", telegram_id)
        if not users:
            await callback.message.answer("Пользователей нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return
        response = "Список пользователей:\n\n"
        for user in users:
            role = "Заказчик" if user["is_customer"] else "Исполнитель" if user["is_executor"] else "Не определена"
            response += (
                f"ID: {user['id']}\n"
                f"Telegram ID: {user['telegram_id']}\n"
                f"Имя: {user['name']}\n"
                f"Роль: {role}\n"
                f"Рейтинг: {user['rating']}\n\n"
            )
        await callback.message.answer(response.strip(), reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        await callback.message.answer(f"Ошибка загрузки пользователей: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.callback_query(F.data == "delete_user")
async def start_delete_user(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID пользователя для удаления:")
    await state.set_state(AdminPanel.delete_user)
    await callback.answer()

@router.message(AdminPanel.delete_user)
async def process_delete_user(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    try:
        user_id = int(message.text)
        await api_request("DELETE", f"user/{user_id}", telegram_id)
        await message.answer(f"Пользователь с ID {user_id} удалён.", reply_markup=get_main_keyboard({"is_admin": True}))
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID.", reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        await message.answer(f"Ошибка удаления пользователя: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()