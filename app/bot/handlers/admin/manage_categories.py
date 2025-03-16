from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.bot.config import ADMIN_TELEGRAM_ID
from ..common.profile import get_main_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)

class CategoryCreation(StatesGroup):
    name = State()

class CategoryUpdate(StatesGroup):
    category_id = State()
    name = State()

@router.message(F.text == "Добавить категорию")
async def start_add_category(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    if telegram_id != ADMIN_TELEGRAM_ID:
        await message.answer("Только администратор может добавлять категории.")
        return
    await message.answer("Введите название новой категории:")
    await state.set_state(CategoryCreation.name)

@router.message(CategoryCreation.name)
async def process_category_name(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    category_name = message.text.strip()
    if not category_name:
        await message.answer("Название категории не может быть пустым. Введите название:")
        return
    try:
        category = await api_request(
            "POST",
            "category/",
            telegram_id,
            data={"name": category_name}
        )
        roles = {"is_admin": True, "is_customer": False, "is_executor": False}
        await message.answer(
            f"Категория '{category['name']}' успешно добавлена!",
            reply_markup=get_main_keyboard(roles)
        )
    except Exception as e:
        logger.error(f"Ошибка добавления категории: {e}")
        roles = {"is_admin": True, "is_customer": False, "is_executor": False}
        await message.answer(
            f"Ошибка добавления категории: {e}",
            reply_markup=get_main_keyboard(roles)
        )
    await state.clear()

@router.message(F.text == "Удалить категорию")
async def start_delete_category(message: Message):
    telegram_id = await get_user_telegram_id(message)
    if telegram_id != ADMIN_TELEGRAM_ID:
        await message.answer("Только администратор может удалять категории.")
        return
    try:
        categories = await api_request("GET", "category/", telegram_id)
        if not categories:
            await message.answer("В системе нет категорий.")
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=cat["name"], callback_data=f"del_cat_{cat['id']}")]
            for cat in categories
        ])
        await message.answer("Выберите категорию для удаления:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка загрузки категорий: {e}")
        await message.answer(f"Ошибка: {e}")

@router.callback_query(F.data.startswith("del_cat_"))
async def process_delete_category(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    category_id = int(callback.data.split("_")[2])
    try:
        await api_request("DELETE", f"category/{category_id}", telegram_id)
        roles = {"is_admin": True, "is_customer": False, "is_executor": False}
        await callback.message.edit_text(
            f"Категория с ID {category_id} успешно удалена!",
            reply_markup=None
        )
        await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard(roles))
    except Exception as e:
        logger.error(f"Ошибка удаления категории: {e}")
        await callback.message.edit_text(f"Ошибка удаления категории: {e}", reply_markup=None)
    await callback.answer()

@router.message(F.text == "Изменить категорию")
async def start_update_category(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    if telegram_id != ADMIN_TELEGRAM_ID:
        await message.answer("Только администратор может изменять категории.")
        return
    try:
        categories = await api_request("GET", "category/", telegram_id)
        if not categories:
            await message.answer("В системе нет категорий.")
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=cat["name"], callback_data=f"upd_cat_{cat['id']}")]
            for cat in categories
        ])
        await message.answer("Выберите категорию для изменения:", reply_markup=keyboard)
        await state.set_state(CategoryUpdate.category_id)
    except Exception as e:
        logger.error(f"Ошибка загрузки категорий: {e}")
        await message.answer(f"Ошибка: {e}")

@router.callback_query(F.data.startswith("upd_cat_"), CategoryUpdate.category_id)
async def process_update_category_id(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[2])
    await state.update_data(category_id=category_id)
    await callback.message.edit_text("Введите новое название категории:")
    await state.set_state(CategoryUpdate.name)
    await callback.answer()

@router.message(CategoryUpdate.name)
async def process_update_category_name(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    new_name = message.text.strip()
    if not new_name:
        await message.answer("Название категории не может быть пустым. Введите новое название:")
        return
    data = await state.get_data()
    category_id = data["category_id"]
    try:
        category = await api_request(
            "PATCH",
            f"category/{category_id}",
            telegram_id,
            data={"name": new_name}
        )
        roles = {"is_admin": True, "is_customer": False, "is_executor": False}
        await message.answer(
            f"Категория обновлена: '{category['name']}'",
            reply_markup=get_main_keyboard(roles)
        )
    except Exception as e:
        logger.error(f"Ошибка изменения категории: {e}")
        roles = {"is_admin": True, "is_customer": False, "is_executor": False}
        await message.answer(
            f"Ошибка изменения категории: {e}",
            reply_markup=get_main_keyboard(roles)
        )
    await state.clear()