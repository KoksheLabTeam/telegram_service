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

class CityCreation(StatesGroup):
    name = State()

class CityUpdate(StatesGroup):
    city_id = State()
    name = State()

@router.message(F.text == "Добавить город")
async def start_add_city(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    logger.info(f"Начало добавления города для пользователя {telegram_id}")
    if telegram_id != ADMIN_TELEGRAM_ID:
        await message.answer("Только администратор может добавлять города.")
        return
    cancel_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отмена")]], resize_keyboard=True)
    await message.answer("Введите название нового города:", reply_markup=cancel_kb)
    await state.set_state(CityCreation.name)
    logger.info(f"Состояние установлено: {await state.get_state()}")

@router.message(CityCreation.name)
async def process_city_name(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    city_name = message.text.strip()
    logger.info(f"Получено название города: {city_name} от {telegram_id}")
    if not city_name:
        await message.answer("Название города не может быть пустым. Введите название:")
        return
    try:
        city = await api_request(
            "POST",
            "city/",
            telegram_id,
            data={"name": city_name}
        )
        roles = {"is_admin": True, "is_customer": False, "is_executor": False}
        await message.answer(
            f"Город '{city['name']}' успешно добавлен!",
            reply_markup=get_main_keyboard(roles)
        )
        logger.info(f"Город '{city['name']}' добавлен")
    except Exception as e:
        logger.error(f"Ошибка добавления города: {e}")
        roles = {"is_admin": True, "is_customer": False, "is_executor": False}
        await message.answer(
            f"Ошибка добавления города: {e}",
            reply_markup=get_main_keyboard(roles)
        )
    await state.clear()
    logger.info("Состояние очищено")

@router.message(F.text == "Удалить город")
async def start_delete_city(message: Message):
    telegram_id = await get_user_telegram_id(message)
    if telegram_id != ADMIN_TELEGRAM_ID:
        await message.answer("Только администратор может удалять города.")
        return
    try:
        cities = await api_request("GET", "city/", telegram_id)
        if not cities:
            await message.answer("В системе нет городов.")
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=city["name"], callback_data=f"del_city_{city['id']}")]
            for city in cities
        ])
        await message.answer("Выберите город для удаления:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка загрузки городов: {e}")
        await message.answer(f"Ошибка: {e}")

@router.callback_query(F.data.startswith("del_city_"))
async def process_delete_city(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    city_id = int(callback.data.split("_")[2])
    try:
        await api_request("DELETE", f"city/{city_id}", telegram_id)
        roles = {"is_admin": True, "is_customer": False, "is_executor": False}
        await callback.message.edit_text(
            f"Город с ID {city_id} успешно удалён!",
            reply_markup=None
        )
        await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard(roles))
    except Exception as e:
        logger.error(f"Ошибка удаления города: {e}")
        await callback.message.edit_text(f"Ошибка удаления города: {e}", reply_markup=None)
    await callback.answer()

@router.message(F.text == "Изменить город")
async def start_update_city(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    if telegram_id != ADMIN_TELEGRAM_ID:
        await message.answer("Только администратор может изменять города.")
        return
    try:
        cities = await api_request("GET", "city/", telegram_id)
        if not cities:
            await message.answer("В системе нет городов.")
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=city["name"], callback_data=f"upd_city_{city['id']}")]
            for city in cities
        ])
        await message.answer("Выберите город для изменения:", reply_markup=keyboard)
        await state.set_state(CityUpdate.city_id)
    except Exception as e:
        logger.error(f"Ошибка загрузки городов: {e}")
        await message.answer(f"Ошибка: {e}")

@router.callback_query(F.data.startswith("upd_city_"), CityUpdate.city_id)
async def process_update_city_id(callback: CallbackQuery, state: FSMContext):
    city_id = int(callback.data.split("_")[2])
    await state.update_data(city_id=city_id)
    await callback.message.edit_text("Введите новое название города:")
    await state.set_state(CityUpdate.name)
    await callback.answer()

@router.message(CityUpdate.name)
async def process_update_city_name(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    new_name = message.text.strip()
    if not new_name:
        await message.answer("Название города не может быть пустым. Введите новое название:")
        return
    data = await state.get_data()
    city_id = data["city_id"]
    try:
        city = await api_request(
            "PATCH",
            f"city/{city_id}",
            telegram_id,
            data={"name": new_name}
        )
        roles = {"is_admin": True, "is_customer": False, "is_executor": False}
        await message.answer(
            f"Город обновлён: '{city['name']}'",
            reply_markup=get_main_keyboard(roles)
        )
    except Exception as e:
        logger.error(f"Ошибка изменения города: {e}")
        roles = {"is_admin": True, "is_customer": False, "is_executor": False}
        await message.answer(
            f"Ошибка изменения города: {e}",
            reply_markup=get_main_keyboard(roles)
        )
    await state.clear()