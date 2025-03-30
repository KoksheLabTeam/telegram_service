from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.config import ADMIN_TELEGRAM_ID, API_URL
from app.bot.utils import api_request  # Импортируем из нового utils.py
from app.bot.handlers.common import get_main_keyboard, get_user_roles
import logging

router = Router()
logger = logging.getLogger(__name__)

class ProfileEditStates(StatesGroup):
    waiting_for_field = State()
    waiting_for_name = State()
    waiting_for_city = State()
    waiting_for_category = State()

async def get_or_create_user(telegram_id: int, full_name: str, username: str | None) -> dict:
    """Получить пользователя по telegram_id или создать нового, если его нет."""
    try:
        # Проверяем наличие пользователя
        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id=telegram_id)
        return user
    except Exception as e:
        if "404" not in str(e):  # Если ошибка не 404, пробрасываем её дальше
            raise
        logger.info(f"Пользователь с telegram_id={telegram_id} не найден, создаём нового")

        # Получаем первый доступный город
        cities = await api_request("GET", f"{API_URL}city/", telegram_id=telegram_id, auth=False)
        if not cities:
            raise Exception("В системе нет городов. Обратитесь к администратору.")
        city_id = cities[0]["id"]

        # Данные для создания пользователя
        user_data = {
            "telegram_id": telegram_id,
            "name": full_name or "Unnamed",
            "username": username,
            "is_customer": True,
            "is_executor": False,
            "city_id": city_id
        }

        # Создаём пользователя
        user = await api_request("POST", f"{API_URL}user/", telegram_id=telegram_id, data=user_data)
        logger.info(f"Пользователь с telegram_id={telegram_id} успешно создан")
        return user

@router.message(Command("start"))
async def start_command(message: Message):
    logger.info(f"Команда /start от пользователя {message.from_user.id}")
    telegram_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username

    try:
        user = await get_or_create_user(telegram_id, full_name, username)
        roles = await get_user_roles(telegram_id)
        await message.answer("Добро пожаловать! Выберите действие в меню ниже:", reply_markup=get_main_keyboard(roles))
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}")
        await message.answer(f"Ошибка: {e}")

@router.message(F.text == "Профиль")
async def show_profile(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id=telegram_id)
        city = await api_request("GET", f"{API_URL}city/{user['city_id']}", telegram_id=telegram_id)
        all_categories = await api_request("GET", f"{API_URL}category/", telegram_id=telegram_id)
        category_ids = user.get('category_ids', []) or []
        categories = [cat['name'] for cat in all_categories if cat['id'] in category_ids]
        roles = []
        if user['is_admin']:
            roles.append("Администратор")
        if user['is_customer']:
            roles.append("Заказчик")
        if user['is_executor']:
            roles.append("Исполнитель")
        role_text = ", ".join(roles) if roles else "Не определена"
        profile_text = (
            f"Ваш профиль:\n\n"
            f"Telegram ID: {user['telegram_id']}\n"
            f"Имя: {user['name']}\n"
            f"Username: @{user['username'] if user['username'] else 'Не указан'}\n"
            f"Город: {city['name']}\n"
            f"Категории: {', '.join(categories) if categories else 'Не указаны'}\n"
            f"Роль: {role_text}\n"
            f"Рейтинг: {user['rating']}\n"
            f"Завершенные заказы: {user['completed_orders']}"
        )
        edit_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Изменить имя", callback_data="edit_name"),
                InlineKeyboardButton(text="Изменить город", callback_data="edit_city")
            ],
            [
                InlineKeyboardButton(text="Изменить категории", callback_data="edit_categories"),
                InlineKeyboardButton(text="Назад", callback_data="back_to_main")
            ]
        ])
        await message.answer(profile_text, reply_markup=edit_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при отображении профиля: {e}")
        roles = await get_user_roles(telegram_id)
        await message.answer(f"Ошибка при загрузке профиля: {e}", reply_markup=get_main_keyboard(roles))

@router.message(F.text == "Список заказов")
async def list_orders(message: Message):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id=telegram_id)
        if not orders:
            await message.answer("У вас нет заказов.", reply_markup=get_main_keyboard(roles))
            return
        response = "Ваши заказы:\n\n"
        status_map = {
            "PENDING": "Ожидает",
            "IN_PROGRESS": "В процессе",
            "COMPLETED": "Завершён",
            "CANCELED": "Отменён"
        }
        for order in orders:
            status = status_map.get(order["status"], order["status"])
            response += f"ID: {order['id']} - {order['title']} ({status})\n"
        await message.answer(response, reply_markup=get_main_keyboard(roles))
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

@router.callback_query(F.data == "edit_name")
async def start_edit_name(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое имя:")
    await state.set_state(ProfileEditStates.waiting_for_name)
    await callback.answer()

@router.callback_query(F.data == "edit_city")
async def start_edit_city(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    try:
        cities = await api_request("GET", f"{API_URL}city/", telegram_id=telegram_id)
        if not cities:
            await callback.message.answer("В системе нет городов. Обратитесь к администратору.")
            return
        cities_list = "\n".join([f"ID: {city['id']} - {city['name']}" for city in cities])
        await callback.message.answer(f"Доступные города:\n{cities_list}\n\nВведите ID нового города:")
        await state.set_state(ProfileEditStates.waiting_for_city)
    except Exception as e:
        logger.error(f"Ошибка при загрузке городов: {e}")
        await callback.message.answer(f"Ошибка: {e}")
    await callback.answer()

@router.callback_query(F.data == "edit_categories")
async def start_edit_categories(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    try:
        categories = await api_request("GET", f"{API_URL}category/", telegram_id=telegram_id)
        if not categories:
            await callback.message.answer("В системе нет категорий. Обратитесь к администратору.")
            return
        categories_list = "\n".join([f"ID: {cat['id']} - {cat['name']}" for cat in categories])
        await callback.message.answer(
            f"Доступные категории:\n{categories_list}\n\n"
            f"Введите ID категорий через запятую (например: 1, 2, 3):"
        )
        await state.set_state(ProfileEditStates.waiting_for_category)
    except Exception as e:
        logger.error(f"Ошибка при загрузке категорий: {e}")
        await callback.message.answer(f"Ошибка: {e}")
    await callback.answer()

@router.message(ProfileEditStates.waiting_for_name)
async def process_name_change(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    new_name = message.text.strip()
    try:
        update_data = {"name": new_name}
        await api_request("PATCH", f"{API_URL}user/me", telegram_id=telegram_id, data=update_data)
        await message.answer(
            f"Имя успешно изменено на '{new_name}'. Выберите действие в меню ниже:",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()
        await show_profile(message, state)
    except Exception as e:
        logger.error(f"Ошибка при изменении имени: {e}")
        roles = await get_user_roles(telegram_id)
        await message.answer(
            f"Ошибка при изменении имени: {e}. Выберите действие в меню ниже:",
            reply_markup=get_main_keyboard(roles)
        )
        await state.clear()

@router.message(ProfileEditStates.waiting_for_city)
async def process_city_change(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    try:
        city_id = int(message.text.strip())
        update_data = {"city_id": city_id}
        logger.info(f"Профиль: PATCH-запрос на {API_URL}user/me с данными: {update_data}")
        await api_request("PATCH", f"{API_URL}user/me", telegram_id=telegram_id, data=update_data)
        await message.answer(
            "Город успешно изменён в вашем профиле.",
            reply_markup=get_main_keyboard(roles)
        )
        await state.clear()
        await show_profile(message, state)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID города.")
    except Exception as e:
        logger.error(f"Ошибка при изменении города: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))
        await state.clear()

@router.message(ProfileEditStates.waiting_for_category)
async def process_category_change(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        category_ids = [int(cat_id.strip()) for cat_id in message.text.split(",")]
        update_data = {"category_ids": category_ids}
        await api_request("PATCH", f"{API_URL}user/me", telegram_id=telegram_id, data=update_data)
        await message.answer(
            "Категории успешно изменены. Выберите действие в меню ниже:",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()
        await show_profile(message, state)
    except ValueError:
        await message.answer("Пожалуйста, введите корректные ID категорий через запятую.")
    except Exception as e:
        logger.error(f"Ошибка при изменении категорий: {e}")
        roles = await get_user_roles(telegram_id)
        await message.answer(
            f"Ошибка: {e}. Выберите действие в меню ниже:",
            reply_markup=get_main_keyboard(roles)
        )
        await state.clear()

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    roles = await get_user_roles(telegram_id)
    await callback.message.edit_text(
        "Выберите действие в меню ниже:",
        reply_markup=get_main_keyboard(roles)
    )
    await callback.answer()