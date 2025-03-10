from aiogram import Router, types
from aiogram.filters import Text
import aiohttp
from app.bot.config import API_URL
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

router = Router()

# Клавиатура для выбора роли
role_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Заказчик"), KeyboardButton(text="Исполнитель")],
        [KeyboardButton(text="Назад")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

async def get_user_telegram_id(message: types.Message) -> int:
    return message.from_user.id

@router.message(Text("Профиль"))
async def profile_command(message: types.Message):
    telegram_id = await get_user_telegram_id(message)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_URL}user/by_telegram_id/{telegram_id}",
            headers={"x-telegram-id": str(telegram_id)}
        ) as resp:
            if resp.status == 200:
                user = await resp.json()
                role = "заказчик" if user.get("isCustomer", False) else "исполнитель" if user.get("isExecutor", False) else "не определена"
                city_id = user.get("cityId", "не указан")
                await message.reply(
                    f"Ваш профиль:\n"
                    f"Имя: {user.get('name', 'не указано')}\n"
                    f"Username: {user.get('username', 'не указано')}\n"
                    f"Роль: {role}\n"
                    f"Город: {city_id}\n"
                    f"Чтобы изменить роль, выберите ниже:",
                    reply_markup=role_keyboard
                )
            else:
                await message.reply(f"Ошибка при получении профиля: {await resp.text()} (Статус: {resp.status})")

@router.message(Text("Заказчик"))
async def set_customer_role(message: types.Message):
    telegram_id = await get_user_telegram_id(message)
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}user/switch-role",
            json={"is_customer": True, "is_executor": False},
            headers={"x-telegram-id": str(telegram_id)}
        ) as resp:
            if resp.status == 200:
                await message.reply("Ваша роль изменена на 'Заказчик'.", reply_markup=main_keyboard)
            else:
                await message.reply(f"Ошибка при смене роли: {await resp.text()}")

@router.message(Text("Исполнитель"))
async def set_executor_role(message: types.Message):
    telegram_id = await get_user_telegram_id(message)
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}user/switch-role",
            json={"is_customer": False, "is_executor": True},
            headers={"x-telegram-id": str(telegram_id)}
        ) as resp:
            if resp.status == 200:
                await message.reply("Ваша роль изменена на 'Исполнитель'.", reply_markup=main_keyboard)
            else:
                await message.reply(f"Ошибка при смене роли: {await resp.text()}")

@router.message(Text("Назад"))
async def back_to_main(message: types.Message):
    await message.reply("Возвращаемся в главное меню.", reply_markup=main_keyboard)