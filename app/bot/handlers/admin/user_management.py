from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL, ADMIN_TELEGRAM_ID
import logging

router = Router()
logger = logging.getLogger(__name__)

class AdminUserStates(StatesGroup):
    delete_user = State()

@router.callback_query(F.data == "list_users")
async def list_users(callback: CallbackQuery):
    logger.info(f"Обработчик list_users вызван для telegram_id={callback.from_user.id}")
    telegram_id = callback.from_user.id
    try:
        users = await api_request("GET", f"{API_URL}user/all", telegram_id)
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
        logger.error(f"Ошибка в list_users: {e}")
        await callback.message.answer(f"Ошибка загрузки пользователей: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.callback_query(F.data == "delete_user")
async def start_delete_user(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Обработчик start_delete_user вызван для telegram_id={callback.from_user.id}")
    telegram_id = callback.from_user.id
    try:
        users = await api_request("GET", f"{API_URL}user/all", telegram_id)
        if not users:
            await callback.message.answer("Пользователей нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return
        response = "Список пользователей:\n\n"
        for user in users:
            role = "Заказчик" if user["is_customer"] else "Исполнитель" if user["is_executor"] else "Не определена"
            response += f"ID: {user['id']} - {user['name']} ({role})\n"
        await callback.message.answer(response.strip() + "\n\nВведите ID пользователя для удаления:")
        await state.set_state(AdminUserStates.delete_user)
    except Exception as e:
        logger.error(f"Ошибка в start_delete_user: {e}")
        await callback.message.answer(f"Ошибка загрузки пользователей: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.message(AdminUserStates.delete_user)
async def process_delete_user(message: Message, state: FSMContext):
    logger.info(f"Обработчик process_delete_user вызван для telegram_id={message.from_user.id}")
    telegram_id = message.from_user.id
    try:
        user_id = int(message.text)
        await api_request("DELETE", f"{API_URL}user/{user_id}", telegram_id)
        await message.answer(f"Пользователь с ID {user_id} удалён.", reply_markup=get_main_keyboard({"is_admin": True}))
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID пользователя.", reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        logger.error(f"Ошибка в process_delete_user: {e}")
        await message.answer(f"Ошибка удаления пользователя: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()