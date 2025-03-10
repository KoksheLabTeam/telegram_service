from aiogram import Router, types
from aiogram.filters import Text
import aiohttp
from app.bot.config import API_URL
from app.bot.handlers.start import main_keyboard

router = Router()


async def get_user_telegram_id(message: types.Message) -> int:
    return message.from_user.id


@router.message(Text("Категории"))
async def list_categories(message: types.Message):
    telegram_id = await get_user_telegram_id(message)
    async with aiohttp.ClientSession() as session:
        async with session.get(
                f"{API_URL}category/",
                headers={"x-telegram-id": str(telegram_id)}
        ) as resp:
            if resp.status == 200:
                categories = await resp.json()
                response = "\n".join([f"{cat['id']}: {cat['name']}" for cat in categories])
                await message.reply(f"Доступные категории:\n{response}", reply_markup=main_keyboard)
            else:
                await message.reply("Ошибка при загрузке категорий.")
