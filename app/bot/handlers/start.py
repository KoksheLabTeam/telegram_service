from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import aiohttp
from app.bot.config import API_URL

router = Router()

# Создаём клавиатуру с кнопками
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Профиль"), KeyboardButton(text="Создать заказ")],
        [KeyboardButton(text="Список заказов"), KeyboardButton(text="Сменить роль")],
        [KeyboardButton(text="Города"), KeyboardButton(text="Категории")],
    ],
    resize_keyboard=True,  # Автоматический размер кнопок
    one_time_keyboard=False  # Клавиатура остаётся после нажатия
)

async def get_user_telegram_id(message: types.Message) -> int:
    return message.from_user.id

@router.message(Command("start"))
async def start_command(message: types.Message):
    telegram_id = await get_user_telegram_id(message)
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
            response_text = await create_resp.text()
            if create_resp.status == 201:
                await message.reply("Добро пожаловать! Вы зарегистрированы.", reply_markup=main_keyboard)
                await message.reply("Пожалуйста, заполните данные для дальнейшей работы (город, категории и т.д.). Нажмите 'Профиль'.")
            elif create_resp.status == 400 and "User with this telegram_id or username already exists" in response_text:
                async with session.get(
                    f"{API_URL}user/by_telegram_id/{telegram_id}",
                    headers={"x-telegram-id": str(telegram_id)}
                ) as user_resp:
                    if user_resp.status == 200:
                        user = await user_resp.json()
                        role = "заказчик" if user.get("isCustomer", False) else "исполнитель" if user.get("isExecutor", False) else "не определена"
                        await message.reply(f"Добро пожаловать обратно! Ваша роль: {role}", reply_markup=main_keyboard)
                        if role == "не определена":
                            await message.reply("Ваши данные не заполнены. Нажмите 'Профиль', чтобы указать роль и другие параметры.")
                    else:
                        await message.reply(f"Ошибка при получении данных: {await user_resp.text()} (Статус: {user_resp.status})")
            else:
                await message.reply(f"Ошибка регистрации: {response_text} (Статус: {create_resp.status})")