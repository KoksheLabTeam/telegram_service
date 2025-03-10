from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import aiohttp
from app.bot.config import API_URL, ADMIN_TELEGRAM_ID
from app.bot.handlers.utils import get_user_telegram_id

router = Router()

# Основная клавиатура
def get_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="Профиль"), KeyboardButton(text="Создать заказ")],
        [KeyboardButton(text="Список заказов"), KeyboardButton(text="Сменить роль")],
        [KeyboardButton(text="Города"), KeyboardButton(text="Категории")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=False)

@router.message(Command("start"))
async def start_command(message: types.Message):
    telegram_id = await get_user_telegram_id(message)
    is_admin = telegram_id == ADMIN_TELEGRAM_ID
    async with aiohttp.ClientSession() as session:
        user_data = {
            "telegram_id": telegram_id,
            "name": message.from_user.full_name or "Unnamed",
            "username": message.from_user.username,
            "is_customer": True,
            "is_executor": False,
            "city_id": 1
        }
        async with session.post(
            f"{API_URL}user/",
            json=user_data,
            headers={"x-telegram-id": str(telegram_id)}
        ) as create_resp:
            if create_resp.status == 201:
                await message.answer("Добро пожаловать! Вы зарегистрированы.", reply_markup=get_main_keyboard(is_admin))
                await message.answer("Пожалуйста, заполните данные для дальнейшей работы. Нажмите 'Профиль'.")
            elif create_resp.status == 400:
                async with session.get(
                    f"{API_URL}user/by_telegram_id/{telegram_id}",
                    headers={"x-telegram-id": str(telegram_id)}
                ) as user_resp:
                    user = await user_resp.json()
                    role = "заказчик" if user.get("is_customer") else "исполнитель" if user.get("is_executor") else "не определена"
                    await message.answer(f"Добро пожаловать обратно! Ваша роль: {role}", reply_markup=get_main_keyboard(is_admin))
                    if role == "не определена":
                        await message.answer("Ваши данные не заполнены. Нажмите 'Профиль', чтобы указать роль и другие параметры.")
            else:
                await message.answer(f"Ошибка регистрации: {await create_resp.text()} (Статус: {create_resp.status})")