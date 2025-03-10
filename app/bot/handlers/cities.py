from aiogram import Router, types
from aiogram.filters import Text
import aiohttp
from app.bot.config import API_URL
from app.bot.handlers.start import main_keyboard

router = Router()

async def get_user_telegram_id(message: types.Message) -> int:
    return message.from_user.id

@router.message(Text("Города"))
async def list_cities(message: types.Message):
    telegram_id = await get_user_telegram_id(message)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_URL}city/",
            headers={"x-telegram-id": str(telegram_id)}
        ) as resp:
            if resp.status == 200:
                cities = await resp.json()
                response = "\n".join([f"{city['id']}: {city['name']}" for city in cities])
                await message.reply(f"Доступные города:\n{response}", reply_markup=main_keyboard)
            else:
                await message.reply("Ошибка при загрузке городов.")