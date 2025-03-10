from aiogram import Router, types
from aiogram.filters import Text
import aiohttp
from app.bot.config import API_URL
from app.bot.handlers.start import main_keyboard  # Импортируем клавиатуру

router = Router()

async def get_user_telegram_id(message: types.Message) -> int:
    return message.from_user.id

@router.message(Text("Создать заказ"))
async def create_order(message: types.Message):
    telegram_id = await get_user_telegram_id(message)
    order_data = {
        "category_id": 1,
        "title": "Тестовый заказ",
        "description": "Проверить работу бота",
        "desired_price": 100.0,
        "due_date": "2025-03-15T12:00:00"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}order/",
            json=order_data,
            headers={"x-telegram-id": str(telegram_id)}
        ) as resp:
            if resp.status == 201:
                await message.reply("Заказ успешно создан!", reply_markup=main_keyboard)
            else:
                await message.reply(f"Ошибка при создании заказа: {await resp.text()}")