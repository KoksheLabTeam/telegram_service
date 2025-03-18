from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "Сменить роль")
async def switch_role_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Заказчик", callback_data="role_customer"),
            InlineKeyboardButton(text="Исполнитель", callback_data="role_executor")
        ],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
    ])
    await message.answer("Выберите новую роль:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("role_"))
async def switch_role_process(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    role = callback.data.split("_")[1]
    try:
        if role == "customer":
            user_data = {"is_customer": True, "is_executor": False}
        elif role == "executor":
            user_data = {"is_customer": False, "is_executor": True}
        else:
            raise ValueError("Недопустимая роль")
        await api_request("PATCH", f"{API_URL}user/me", telegram_id, data=user_data)
        roles = await get_user_roles(telegram_id)
        # Удаляем inline-кнопки и возвращаем нижнюю панель
        await callback.message.edit_text(
            f"Роль изменена на {'Заказчик' if role == 'customer' else 'Исполнитель'}!"
        )
        await callback.message.answer(
            "Выберите действие в меню ниже:",
            reply_markup=get_main_keyboard(roles)
        )
    except Exception as e:
        logger.error(f"Ошибка смены роли: {e}")
        roles = await get_user_roles(telegram_id)
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.message.answer(
            "Выберите действие в меню ниже:",
            reply_markup=get_main_keyboard(roles)
        )
    await callback.answer()

@router.callback_query(F.data == "cancel")
async def switch_role_cancel(callback: CallbackQuery, state: FSMContext):
    roles = await get_user_roles(callback.from_user.id)
    await callback.message.edit_text("Действие отменено.")
    await callback.message.answer(
        "Выберите действие в меню ниже:",
        reply_markup=get_main_keyboard(roles)
    )
    await callback.answer()