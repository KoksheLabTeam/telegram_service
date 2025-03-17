from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.common import api_request, get_main_keyboard
from app.bot.config import API_URL
import logging

router = Router()
logger = logging.getLogger(__name__)

class AdminCityStates(StatesGroup):
    add_city = State()
    edit_city_select = State()
    edit_city_name = State()
    delete_city = State()

@router.callback_query(F.data == "list_cities")
async def list_cities(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    try:
        cities = await api_request("GET", f"{API_URL}city/", telegram_id)
        if not cities:
            await callback.message.answer("Городов нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return
        response = "Список городов:\n\n"
        for city in cities:
            response += f"ID: {city['id']} - {city['name']}\n"
        await callback.message.answer(response.strip(), reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        logger.error(f"Ошибка в list_cities: {e}")
        await callback.message.answer(f"Ошибка загрузки городов: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.callback_query(F.data == "add_city")
async def start_add_city(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название нового города:")
    await state.set_state(AdminCityStates.add_city)
    await callback.answer()

@router.message(AdminCityStates.add_city)
async def process_add_city(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    city_name = message.text.strip()
    try:
        data = {"name": city_name}
        await api_request("POST", f"{API_URL}city/", telegram_id, data=data)
        await message.answer(f"Город '{city_name}' добавлен.", reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        logger.error(f"Ошибка в process_add_city: {e}")
        await message.answer(f"Ошибка добавления города: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()

@router.callback_query(F.data == "edit_city")
async def start_edit_city(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    try:
        cities = await api_request("GET", f"{API_URL}city/", telegram_id)
        if not cities:
            await callback.message.answer("Городов нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return
        response = "Список городов:\n\n"
        for city in cities:
            response += f"ID: {city['id']} - {city['name']}\n"
        await callback.message.answer(response.strip() + "\n\nВведите ID города для изменения:")
        await state.set_state(AdminCityStates.edit_city_select)
    except Exception as e:
        logger.error(f"Ошибка в start_edit_city: {e}")
        await callback.message.answer(f"Ошибка загрузки городов: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.message(AdminCityStates.edit_city_select)
async def process_edit_city_select(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        city_id = int(message.text)
        city = await api_request("GET", f"{API_URL}city/{city_id}", telegram_id)
        await state.update_data(city_id=city_id)
        await message.answer(f"Текущее название: {city['name']}\nВведите новое название города:")
        await state.set_state(AdminCityStates.edit_city_name)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID города.")
    except Exception as e:
        logger.error(f"Ошибка в process_edit_city_select: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
        await state.clear()

@router.message(AdminCityStates.edit_city_name)
async def process_edit_city_name(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        data = await state.get_data()
        city_id = data["city_id"]
        new_name = message.text.strip()
        update_data = {"name": new_name}
        await api_request("PATCH", f"{API_URL}city/{city_id}", telegram_id, data=update_data)
        await message.answer(f"Город с ID {city_id} изменён на '{new_name}'.", reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        logger.error(f"Ошибка в process_edit_city_name: {e}")
        await message.answer(f"Ошибка изменения города: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()

@router.callback_query(F.data == "delete_city")
async def start_delete_city(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    try:
        cities = await api_request("GET", f"{API_URL}city/", telegram_id)
        if not cities:
            await callback.message.answer("Городов нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return
        response = "Список городов:\n\n"
        for city in cities:
            response += f"ID: {city['id']} - {city['name']}\n"
        await callback.message.answer(response.strip() + "\n\nВведите ID города для удаления:")
        await state.set_state(AdminCityStates.delete_city)
    except Exception as e:
        logger.error(f"Ошибка в start_delete_city: {e}")
        await callback.message.answer(f"Ошибка загрузки городов: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.message(AdminCityStates.delete_city)
async def process_delete_city(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        city_id = int(message.text)
        await api_request("DELETE", f"{API_URL}city/{city_id}", telegram_id)
        await message.answer(f"Город с ID {city_id} удалён.", reply_markup=get_main_keyboard({"is_admin": True}))
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID города.")
    except Exception as e:
        logger.error(f"Ошибка в process_delete_city: {e}")
        await message.answer(f"Ошибка удаления города: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()