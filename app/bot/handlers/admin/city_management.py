from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL, ADMIN_TELEGRAM_ID
import logging

router = Router()
logger = logging.getLogger(__name__)

class AdminCityStates(StatesGroup):
    add_city = State()
    rename_city_select = State()  # Новое состояние для выбора города при переименовании
    rename_city_name = State()    # Новое состояние для ввода нового названия
    delete_city = State()

@router.callback_query(F.data == "list_cities")
async def list_cities(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_admin"] or telegram_id != ADMIN_TELEGRAM_ID:
        await callback.message.answer(
            "Доступ только для администраторов.",
            reply_markup=get_main_keyboard(roles)
        )
        return
    try:
        cities = await api_request("GET", f"{API_URL}city/", telegram_id)
        if not cities:
            await callback.message.answer(
                "Городов нет.",
                reply_markup=get_main_keyboard(roles)
            )
            return
        response = "Список городов:\n\n"
        for city in cities:
            response += f"ID: {city['id']} - {city['name']}\n"
        await callback.message.answer(response.strip(), reply_markup=get_main_keyboard(roles))
    except Exception as e:
        logger.error(f"Ошибка в list_cities: {e}")
        await callback.message.answer(
            f"Ошибка загрузки городов: {e}",
            reply_markup=get_main_keyboard(roles)
        )

@router.callback_query(F.data == "add_city")
async def start_add_city(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_admin"] or telegram_id != ADMIN_TELEGRAM_ID:
        await callback.message.answer(
            "Доступ только для администраторов.",
            reply_markup=get_main_keyboard(roles)
        )
        return
    await callback.message.answer("Введите название нового города:")
    await state.set_state(AdminCityStates.add_city)

@router.message(AdminCityStates.add_city)
async def process_add_city(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    city_name = message.text.strip()
    if not city_name:
        await message.answer("Название города не может быть пустым.")
        return
    try:
        data = {"name": city_name}
        await api_request("POST", f"{API_URL}city/", telegram_id, data=data)
        await message.answer(
            f"Город '{city_name}' добавлен.",
            reply_markup=get_main_keyboard(roles)
        )
    except Exception as e:
        logger.error(f"Ошибка в process_add_city: {e}")
        error_msg = "Ошибка добавления города. Возможно, город с таким названием уже существует." if "уже существует" in str(e) else f"Ошибка: {e}"
        await message.answer(error_msg, reply_markup=get_main_keyboard(roles))
    await state.clear()

@router.callback_query(F.data == "rename_city")
async def start_rename_city(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_admin"] or telegram_id != ADMIN_TELEGRAM_ID:
        await callback.message.answer(
            "Доступ только для администраторов.",
            reply_markup=get_main_keyboard(roles)
        )
        return
    # Сбрасываем любое предыдущее состояние
    await state.clear()
    try:
        cities = await api_request("GET", f"{API_URL}city/", telegram_id)
        if not cities:
            await callback.message.answer(
                "Городов нет.",
                reply_markup=get_main_keyboard(roles)
            )
            return
        cities_list = "\n".join([f"ID: {city['id']} - {city['name']}" for city in cities])
        await callback.message.answer(
            f"Переименование города (админ-панель):\n{cities_list}\n\nВведите ID города для изменения названия:",
            reply_markup=get_main_keyboard(roles)
        )
        await state.set_state(AdminCityStates.rename_city_select)
        logger.info(f"Установлено состояние AdminCityStates.rename_city_select для telegram_id={telegram_id}")
    except Exception as e:
        logger.error(f"Ошибка в start_rename_city: {e}")
        await callback.message.answer(
            f"Ошибка загрузки городов: {e}",
            reply_markup=get_main_keyboard(roles)
        )
    await callback.answer()

@router.message(AdminCityStates.rename_city_select)
async def process_rename_city_select(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_admin"] or telegram_id != ADMIN_TELEGRAM_ID:
        await message.answer(
            "Доступ только для администраторов.",
            reply_markup=get_main_keyboard(roles)
        )
        await state.clear()
        return
    try:
        city_id = int(message.text.strip())
        city = await api_request("GET", f"{API_URL}city/{city_id}", telegram_id)
        await state.update_data(city_id=city_id, old_name=city["name"])
        await message.answer(
            f"Текущее название: {city['name']}\nВведите новое название для города (ID: {city_id}):"
        )
        await state.set_state(AdminCityStates.rename_city_name)
        logger.info(f"Переход в AdminCityStates.rename_city_name для city_id={city_id}")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID города.")
    except Exception as e:
        logger.error(f"Ошибка в process_rename_city_select: {e}")
        error_msg = "Город не найден." if "404" in str(e) else f"Ошибка: {e}"
        await message.answer(error_msg, reply_markup=get_main_keyboard(roles))
        await state.clear()

@router.message(AdminCityStates.rename_city_name)
async def process_rename_city_name(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_admin"] or telegram_id != ADMIN_TELEGRAM_ID:
        await message.answer(
            "Доступ только для администраторов.",
            reply_markup=get_main_keyboard(roles)
        )
        await state.clear()
        return
    new_name = message.text.strip()
    if not new_name:
        await message.answer("Название города не может быть пустым.")
        return
    try:
        data = await state.get_data()
        city_id = data["city_id"]
        old_name = data["old_name"]
        update_data = {"name": new_name}
        logger.info(f"Админ-панель: PATCH-запрос на {API_URL}city/{city_id} с данными: {update_data}")
        updated_city = await api_request("PATCH", f"{API_URL}city/{city_id}", telegram_id, data=update_data)
        await message.answer(
            f"Город с ID {city_id} переименован с '{old_name}' на '{updated_city['name']}'.",
            reply_markup=get_main_keyboard(roles)
        )
    except Exception as e:
        logger.error(f"Ошибка в process_rename_city_name: {e}")
        error_msg = "Город с таким названием уже существует." if "уже существует" in str(e) else f"Ошибка: {e}"
        await message.answer(error_msg, reply_markup=get_main_keyboard(roles))
    await state.clear()

@router.callback_query(F.data == "delete_city")
async def start_delete_city(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_admin"] or telegram_id != ADMIN_TELEGRAM_ID:
        await callback.message.answer(
            "Доступ только для администраторов.",
            reply_markup=get_main_keyboard(roles)
        )
        return
    try:
        cities = await api_request("GET", f"{API_URL}city/", telegram_id)
        if not cities:
            await callback.message.answer(
                "Городов нет.",
                reply_markup=get_main_keyboard(roles)
            )
            return
        response = "Список городов:\n\n"
        for city in cities:
            response += f"ID: {city['id']} - {city['name']}\n"
        await callback.message.answer(
            response.strip() + "\n\nВведите ID города для удаления:",
            reply_markup=get_main_keyboard(roles)
        )
        await state.set_state(AdminCityStates.delete_city)
    except Exception as e:
        logger.error(f"Ошибка в start_delete_city: {e}")
        await callback.message.answer(
            f"Ошибка загрузки городов: {e}",
            reply_markup=get_main_keyboard(roles)
        )

@router.message(AdminCityStates.delete_city)
async def process_delete_city(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    try:
        city_id = int(message.text.strip())
        await api_request("DELETE", f"{API_URL}city/{city_id}", telegram_id)
        await message.answer(
            f"Город с ID {city_id} удалён.",
            reply_markup=get_main_keyboard(roles)
        )
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID города.")
    except Exception as e:
        logger.error(f"Ошибка в process_delete_city: {e}")
        error_msg = "Город не найден или не может быть удалён (возможно, к нему привязаны пользователи)." if "404" in str(e) else f"Ошибка: {e}"
        await message.answer(error_msg, reply_markup=get_main_keyboard(roles))
    await state.clear()