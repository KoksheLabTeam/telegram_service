from aiogram import Router, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.bot.config import ADMIN_TELEGRAM_ID, API_URL
from app.bot.handlers.start import get_main_keyboard
from app.bot.handlers.utils import api_request

router = Router()

@router.message(F.text == "Админ-панель", lambda msg: msg.from_user.id == ADMIN_TELEGRAM_ID)
async def admin_panel(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="Удалить категорию", callback_data="delete_category"),
        InlineKeyboardButton(text="Удалить город", callback_data="delete_city"),
        InlineKeyboardButton(text="Назад", callback_data="back")
    )
    await message.answer("Админ-панель:", reply_markup=keyboard)

@router.callback_query(F.data == "delete_category")
async def delete_category_start(callback: types.CallbackQuery):
    telegram_id = callback.from_user.id
    try:
        categories = await api_request("GET", f"{API_URL}category/", telegram_id)
        keyboard = InlineKeyboardMarkup(row_width=2)
        for cat in categories:
            keyboard.add(InlineKeyboardButton(
                text=cat["name"],
                callback_data=f"delete_category_{cat['id']}"
            ))
        keyboard.add(InlineKeyboardButton(text="Назад", callback_data="back"))
        await callback.message.answer("Выберите категорию для удаления:", reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("delete_category_"))
async def delete_category_confirm(callback: types.CallbackQuery):
    category_id = int(callback.data.split("_")[2])
    telegram_id = callback.from_user.id
    try:
        await api_request("DELETE", f"{API_URL}category/{category_id}", telegram_id)
        await callback.message.answer("Категория удалена.", reply_markup=get_main_keyboard())
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())
    await callback.answer()