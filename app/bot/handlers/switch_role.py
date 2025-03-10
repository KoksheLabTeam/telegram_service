from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton  # Добавляем импорты
import aiohttp
from app.bot.config import API_URL, ADMIN_TELEGRAM_ID
from app.bot.handlers.start import get_main_keyboard
from app.bot.handlers.utils import api_request, get_user_telegram_id

router = Router()


@router.message(F.text == "Сменить роль")
async def switch_role_handler(message: types.Message):
    telegram_id = await get_user_telegram_id(message)
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="Заказчик", callback_data="role_customer"),
        InlineKeyboardButton(text="Исполнитель", callback_data="role_executor"),
        InlineKeyboardButton(text="Назад", callback_data="back")
    )
    await message.answer("Выберите новую роль:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("role_"))
async def change_role(callback: types.CallbackQuery):
    role = callback.data.split("_")[1]
    telegram_id = callback.from_user.id
    is_customer = role == "customer"
    is_executor = role == "executor"

    # Проверяем, чтобы пользователь не был одновременно заказчиком и исполнителем
    if is_customer and is_executor:
        await callback.message.answer("Вы не можете быть одновременно заказчиком и исполнителем!",
                                      reply_markup=get_main_keyboard())
        await callback.answer()
        return

    try:
        # Отправляем запрос на обновление роли
        await api_request(
            method="PATCH",
            url=f"{API_URL}user/me",
            telegram_id=telegram_id,
            json={"is_customer": is_customer, "is_executor": is_executor}
        )
        role_name = "заказчик" if is_customer else "исполнитель"
        await callback.message.answer(f"Ваша роль изменена на: {role_name}", reply_markup=get_main_keyboard())
    except Exception as e:
        await callback.message.answer(f"Ошибка при смене роли: {e}", reply_markup=get_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "back")
async def back_to_main(callback: types.CallbackQuery):
    telegram_id = callback.from_user.id
    is_admin = telegram_id == ADMIN_TELEGRAM_ID
    await callback.message.answer("Возвращаемся в главное меню.", reply_markup=get_main_keyboard(is_admin))
    await callback.answer()