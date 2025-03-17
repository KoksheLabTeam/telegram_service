from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.common import api_request, get_main_keyboard
from app.bot.config import API_URL
import logging

router = Router()
logger = logging.getLogger(__name__)

class AdminCategoryStates(StatesGroup):
    add_category = State()
    edit_category_select = State()
    edit_category_name = State()
    delete_category = State()

@router.callback_query(F.data == "list_categories")  # Новый обработчик
async def list_categories(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    try:
        categories = await api_request("GET", f"{API_URL}category/", telegram_id)
        if not categories:
            await callback.message.answer("Категорий нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return
        response = "Список категорий:\n\n"
        for category in categories:
            response += f"ID: {category['id']} - {category['name']}\n"
        await callback.message.answer(response.strip(), reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        logger.error(f"Ошибка в list_categories: {e}")
        await callback.message.answer(f"Ошибка загрузки категорий: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.callback_query(F.data == "add_category")
async def start_add_category(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    try:
        # Показываем текущий список категорий перед добавлением
        categories = await api_request("GET", f"{API_URL}category/", telegram_id)
        if not categories:
            await callback.message.answer("Категорий нет.\n\nВведите название новой категории:")
        else:
            response = "Текущие категории:\n\n"
            for category in categories:
                response += f"ID: {category['id']} - {category['name']}\n"
            response += "\nВведите название новой категории:"
            await callback.message.answer(response.strip())
        await state.set_state(AdminCategoryStates.add_category)
    except Exception as e:
        logger.error(f"Ошибка в start_add_category: {e}")
        await callback.message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.message(AdminCategoryStates.add_category)
async def process_add_category(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    category_name = message.text.strip()
    try:
        data = {"name": category_name}
        await api_request("POST", f"{API_URL}category/", telegram_id, data=data)
        await message.answer(f"Категория '{category_name}' добавлена.", reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        logger.error(f"Ошибка в process_add_category: {e}")
        await message.answer(f"Ошибка добавления категории: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()

@router.callback_query(F.data == "edit_category")
async def start_edit_category(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    try:
        categories = await api_request("GET", f"{API_URL}category/", telegram_id)
        if not categories:
            await callback.message.answer("Категорий нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return
        response = "Список категорий:\n\n"
        for category in categories:
            response += f"ID: {category['id']} - {category['name']}\n"
        await callback.message.answer(response.strip() + "\n\nВведите ID категории для изменения:")
        await state.set_state(AdminCategoryStates.edit_category_select)
    except Exception as e:
        logger.error(f"Ошибка в start_edit_category: {e}")
        await callback.message.answer(f"Ошибка загрузки категорий: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.message(AdminCategoryStates.edit_category_select)
async def process_edit_category_select(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        category_id = int(message.text)
        category = await api_request("GET", f"{API_URL}category/{category_id}", telegram_id)
        await state.update_data(category_id=category_id)
        await message.answer(f"Текущее название: {category['name']}\nВведите новое название категории:")
        await state.set_state(AdminCategoryStates.edit_category_name)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID категории.")
    except Exception as e:
        logger.error(f"Ошибка в process_edit_category_select: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
        await state.clear()

@router.message(AdminCategoryStates.edit_category_name)
async def process_edit_category_name(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        data = await state.get_data()
        category_id = data["category_id"]
        new_name = message.text.strip()
        update_data = {"name": new_name}
        await api_request("PATCH", f"{API_URL}category/{category_id}", telegram_id, data=update_data)
        await message.answer(f"Категория с ID {category_id} изменена на '{new_name}'.", reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        logger.error(f"Ошибка в process_edit_category_name: {e}")
        await message.answer(f"Ошибка изменения категории: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()

@router.callback_query(F.data == "delete_category")
async def start_delete_category(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    try:
        categories = await api_request("GET", f"{API_URL}category/", telegram_id)
        if not categories:
            await callback.message.answer("Категорий нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return
        response = "Список категорий:\n\n"
        for category in categories:
            response += f"ID: {category['id']} - {category['name']}\n"
        await callback.message.answer(response.strip() + "\n\nВведите ID категории для удаления:")
        await state.set_state(AdminCategoryStates.delete_category)
    except Exception as e:
        logger.error(f"Ошибка в start_delete_category: {e}")
        await callback.message.answer(f"Ошибка загрузки категорий: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.message(AdminCategoryStates.delete_category)
async def process_delete_category(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        category_id = int(message.text)
        await api_request("DELETE", f"{API_URL}category/{category_id}", telegram_id)
        await message.answer(f"Категория с ID {category_id} удалена.", reply_markup=get_main_keyboard({"is_admin": True}))
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID категории.")
    except Exception as e:
        logger.error(f"Ошибка в process_delete_category: {e}")
        await message.answer(f"Ошибка удаления категории: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()