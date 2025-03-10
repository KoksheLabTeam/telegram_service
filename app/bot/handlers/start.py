from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp
from app.bot.config import API_URL, ADMIN_TELEGRAM_ID
from app.bot.handlers.utils import get_user_telegram_id, api_request, create_cities_keyboard, create_categories_keyboard

router = Router()

def get_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="Профиль"), KeyboardButton(text="Создать заказ")],
        [KeyboardButton(text="Список заказов"), KeyboardButton(text="Сменить роль")],
        [KeyboardButton(text="Города"), KeyboardButton(text="Категории")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

@router.message(Command("start"))
async def start_command(message: types.Message):
    telegram_id = await get_user_telegram_id(message)
    is_admin = telegram_id == ADMIN_TELEGRAM_ID
    user_data = {
        "telegram_id": telegram_id,
        "name": message.from_user.full_name or "Unnamed",
        "username": message.from_user.username,
        "is_customer": True,
        "is_executor": False,
        "city_id": 1
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}user/", json=user_data, headers={"x-telegram-id": str(telegram_id)}) as create_resp:
            if create_resp.status in [200, 201]:
                await message.answer("Добро пожаловать! Вы зарегистрированы.", reply_markup=get_main_keyboard(is_admin))
            elif create_resp.status == 400:
                async with session.get(f"{API_URL}user/by_telegram_id/{telegram_id}", headers={"x-telegram-id": str(telegram_id)}) as user_resp:
                    user = await user_resp.json()
                    role = "Заказчик" if user.get("is_customer") else "Исполнитель" if user.get("is_executor") else "Не определена"
                    await message.answer(f"Добро пожаловать обратно! Ваша роль: {role}", reply_markup=get_main_keyboard(is_admin))
            else:
                await message.answer(f"Ошибка регистрации: {await create_resp.text()} (Статус: {create_resp.status})")

@router.message(F.text == "Профиль")
async def show_profile(message: types.Message):
    telegram_id = message.from_user.id
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}user/by_telegram_id/{telegram_id}", headers={"x-telegram-id": str(telegram_id)}) as user_resp:
            user = await user_resp.json()
            role = "Заказчик" if user.get("is_customer") else "Исполнитель" if user.get("is_executor") else "Не определена"
            city = user.get("city", {}).get("name", "Не указан")
            text = f"Ваш профиль:\nИмя: {user['name']}\nUsername: {user['username']}\nРоль: {role}\nГород: {city}"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Изменить имя", callback_data="update_name")],
                [InlineKeyboardButton(text="Изменить город", callback_data="update_city")],
                [InlineKeyboardButton(text="Изменить категории", callback_data="update_categories")],
                [InlineKeyboardButton(text="Назад", callback_data="back")]
            ])
            await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data == "update_city")
async def update_city(callback: types.CallbackQuery):
    telegram_id = callback.from_user.id
    try:
        cities = await api_request("GET", f"{API_URL}city/", telegram_id)
        keyboard = create_cities_keyboard(cities)
        await callback.message.answer("Выберите город:", reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}")
    await callback.answer()

@router.callback_query(F.data.startswith("city_"))
async def select_city(callback: types.CallbackQuery):
    city_id = int(callback.data.split("_")[1])
    telegram_id = callback.from_user.id
    try:
        await api_request("PATCH", f"{API_URL}user/me", telegram_id, json={"city_id": city_id})
        await callback.message.answer("Город успешно обновлен!", reply_markup=get_main_keyboard())
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}")
    await callback.answer()

@router.callback_query(F.data == "update_categories")
async def update_categories(callback: types.CallbackQuery):
    telegram_id = callback.from_user.id
    try:
        categories = await api_request("GET", f"{API_URL}category/", telegram_id)
        keyboard = create_categories_keyboard(categories)
        await callback.message.answer("Выберите категории:", reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}")
    await callback.answer()

@router.callback_query(F.data.startswith("category_"))
async def select_category(callback: types.CallbackQuery):
    category_id = int(callback.data.split("_")[1])
    telegram_id = callback.from_user.id
    try:
        await api_request("PATCH", f"{API_URL}user/me", telegram_id, json={"category_ids": [category_id]})
        await callback.message.answer("Категория успешно обновлена!", reply_markup=get_main_keyboard())
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}")
    await callback.answer()
