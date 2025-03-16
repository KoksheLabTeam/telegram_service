from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, KeyboardButton, \
    ReplyKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.bot.config import ADMIN_TELEGRAM_ID, API_URL
import logging

router = Router()
logger = logging.getLogger(__name__)

class ProfileStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_city = State()
    waiting_for_category = State()

def get_main_keyboard(roles: dict) -> ReplyKeyboardMarkup:
    logger.debug(f"Создание клавиатуры для ролей: {roles}")
    buttons = []
    if roles["is_admin"]:
        buttons.append([KeyboardButton(text="Админ панель")])
    if roles["is_customer"]:
        buttons.append([KeyboardButton(text="Создать заказ")])
        buttons.append([KeyboardButton(text="Мои заказы")])
    if roles["is_executor"]:
        buttons.append([KeyboardButton(text="Создать предложение")])
        buttons.append([KeyboardButton(text="Мои предложения")])
    buttons.append([KeyboardButton(text="Профиль"), KeyboardButton(text="Сменить роль")])
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    logger.debug(f"Клавиатура создана: {keyboard}")
    return keyboard

@router.message(F.text == "Профиль")
async def show_profile(message: Message):
    telegram_id = await get_user_telegram_id(message)
    try:
        user = await api_request("GET", "user/me", telegram_id)
        role = "Заказчик" if user["is_customer"] else "Исполнитель" if user["is_executor"] else "Не определена"
        city = await api_request("GET", f"city/{user['city_id']}", telegram_id)
        categories = [cat["name"] for cat in await api_request("GET", "category/", telegram_id) if cat["id"] in [c["id"] for c in user.get("categories", [])]]
        response = (
            f"Ваш профиль:\n"
            f"Имя: {user['name']}\n"
            f"Username: @{user['username'] or 'не указан'}\n"
            f"Роль: {role}\n"
            f"Город: {city['name']}\n"
            f"Категории: {', '.join(categories) or 'не выбраны'}\n"
            f"Рейтинг: {user['rating']}\n"
            f"Завершённых заказов: {user['completed_orders']}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить имя", callback_data="edit_name"),
             InlineKeyboardButton(text="Изменить город", callback_data="edit_city")],
            [InlineKeyboardButton(text="Изменить категории", callback_data="edit_categories"),
             InlineKeyboardButton(text="Назад", callback_data="back")]
        ])
        await message.answer(response, reply_markup=keyboard)
    except Exception as e:
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": False}
        await message.answer(f"Ошибка загрузки профиля: {e}", reply_markup=get_main_keyboard(roles))

@router.callback_query(F.data == "edit_name")
async def start_edit_name(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое имя:")
    await state.set_state(ProfileStates.waiting_for_name)
    await callback.answer()

@router.message(ProfileStates.waiting_for_name)
async def process_edit_name(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    try:
        name = message.text.strip()
        await api_request("PATCH", "user/me", telegram_id, data={"name": name})
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_customer": True}
        await message.answer(f"Имя обновлено: {name}", reply_markup=get_main_keyboard(roles))
    except Exception as e:
        await message.answer(f"Ошибка обновления имени: {e}", reply_markup=get_main_keyboard({"is_customer": True}))
    await state.clear()

@router.callback_query(F.data == "edit_city")
async def start_edit_city(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    cities = await api_request("GET", "city/", telegram_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=city["name"], callback_data=f"city_{city['id']}")] for city in cities
    ])
    await callback.message.answer("Выберите новый город:", reply_markup=keyboard)
    await state.set_state(ProfileStates.waiting_for_city)
    await callback.answer()

@router.callback_query(F.data.startswith("city_"), ProfileStates.waiting_for_city)
async def process_edit_city(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    city_id = int(callback.data.split("_")[1])
    try:
        await api_request("PATCH", "user/me", telegram_id, data={"city_id": city_id})
        city = await api_request("GET", f"city/{city_id}", telegram_id)
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": True}
        await callback.message.answer(f"Город обновлён: {city['name']}", reply_markup=get_main_keyboard(roles))
    except Exception as e:
        await callback.message.answer(f"Ошибка обновления города: {e}", reply_markup=get_main_keyboard({"is_executor": True}))
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "edit_categories")
async def start_edit_categories(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    categories = await api_request("GET", "category/", telegram_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cat["name"], callback_data=f"cat_{cat['id']}")] for cat in categories
    ])
    await callback.message.answer("Выберите категории (можно выбрать несколько, затем нажмите 'Готово'):", reply_markup=keyboard)
    await state.set_state(ProfileStates.waiting_for_category)
    await state.update_data(selected_categories=[])
    await callback.answer()

@router.callback_query(F.data.startswith("cat_"), ProfileStates.waiting_for_category)
async def process_category_selection(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    selected = data.get("selected_categories", [])
    if category_id not in selected:
        selected.append(category_id)
    await state.update_data(selected_categories=selected)
    await callback.answer(f"Категория ID {category_id} добавлена.")

@router.message(F.text == "Готово", ProfileStates.waiting_for_category)
async def finish_categories(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    data = await state.get_data()
    selected_categories = data.get("selected_categories", [])
    try:
        await api_request("PATCH", "user/me", telegram_id, data={"category_ids": selected_categories})
        await message.answer("Категории обновлены!", reply_markup=get_main_keyboard({"is_executor": True}))
    except Exception as e:
        await message.answer(f"Ошибка обновления категорий: {e}", reply_markup=get_main_keyboard({"is_executor": True}))
    await state.clear()