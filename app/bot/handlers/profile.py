from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.config import API_URL
from app.bot.handlers.start import get_main_keyboard
from app.bot.handlers.utils import api_request, create_cities_keyboard, create_back_keyboard

router = Router()

class UpdateProfileStates(StatesGroup):
    SELECT_FIELD = State()
    ENTER_VALUE = State()
    SELECT_CITY = State()

@router.message(F.text == "Профиль")
async def show_profile(message: types.Message):
    telegram_id = message.from_user.id
    try:
        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
        role = "заказчик" if user.get("is_customer") else "исполнитель" if user.get("is_executor") else "не определена"
        city = user.get("city", {}).get("name", "не указан") if user.get("city") else "не указан"
        text = (
            f"Ваш профиль:\n"
            f"Имя: {user['name']}\n"
            f"Username: {user['username']}\n"
            f"Роль: {role}\n"
            f"Город: {city}\n"
            f"Чтобы изменить данные, выберите ниже:"
        )
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton(text="Имя", callback_data="update_name"),
            InlineKeyboardButton(text="Город", callback_data="update_city"),
            InlineKeyboardButton(text="Назад", callback_data="back")
        )
        await message.answer(text, reply_markup=keyboard)
    except Exception as e:
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())

@router.callback_query(F.data == "update_name")
async def update_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое имя:", reply_markup=create_back_keyboard())
    await state.set_state(UpdateProfileStates.ENTER_VALUE)
    await state.update_data(field="name")
    await callback.answer()

@router.callback_query(F.data == "update_city")
async def update_city(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    try:
        cities = await api_request("GET", f"{API_URL}city/", telegram_id)
        await callback.message.answer(
            "Выберите город:",
            reply_markup=create_cities_keyboard(cities)
        )
        await state.set_state(UpdateProfileStates.SELECT_CITY)
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())
    await callback.answer()

@router.message(UpdateProfileStates.ENTER_VALUE)
async def process_value(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    data = await state.get_data()
    field = data["field"]
    value = message.text
    telegram_id = message.from_user.id
    try:
        await api_request("PATCH", f"{API_URL}user/me", telegram_id, json={field: value})
        await message.answer(f"{field} успешно обновлено!", reply_markup=get_main_keyboard())
    except Exception as e:
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())
    await state.clear()

@router.callback_query(F.data.startswith("city_"))
async def select_city(callback: types.CallbackQuery, state: FSMContext):
    city_id = int(callback.data.split("_")[1])
    telegram_id = callback.from_user.id
    try:
        await api_request("PATCH", f"{API_URL}user/me", telegram_id, json={"city_id": city_id})
        await callback.message.answer("Город успешно обновлен!", reply_markup=get_main_keyboard())
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())
    await state.clear()
    await callback.answer()