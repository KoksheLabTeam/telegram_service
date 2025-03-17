from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from app.bot.config import ADMIN_TELEGRAM_ID
from app.bot.handlers.common import get_main_keyboard, get_user_roles
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "Админ панель")
async def admin_panel(message: Message):
    logger.info(f"Попытка доступа к админ-панели от пользователя {message.from_user.id}")
    if message.from_user.id != ADMIN_TELEGRAM_ID:
        logger.warning(f"Доступ запрещен для пользователя {message.from_user.id}")
        await message.answer("Доступ запрещен!")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Список пользователей", callback_data="list_users"),
         InlineKeyboardButton(text="Список заказов", callback_data="list_orders")],
        [InlineKeyboardButton(text="Удалить пользователя", callback_data="delete_user"),
         InlineKeyboardButton(text="Удалить заказ", callback_data="delete_order")],
        [InlineKeyboardButton(text="Список городов", callback_data="list_cities"),
         InlineKeyboardButton(text="Добавить город", callback_data="add_city")],
        [InlineKeyboardButton(text="Изменить город", callback_data="edit_city"),
         InlineKeyboardButton(text="Удалить город", callback_data="delete_city")],
        [InlineKeyboardButton(text="Список категорий", callback_data="list_categories"),  # Новая кнопка
         InlineKeyboardButton(text="Добавить категорию", callback_data="add_category")],
        [InlineKeyboardButton(text="Изменить категорию", callback_data="edit_category"),
         InlineKeyboardButton(text="Удалить категорию", callback_data="delete_category")],
        [InlineKeyboardButton(text="Назад", callback_data="back")]
    ])
    await message.answer("Админ-панель:", reply_markup=keyboard)