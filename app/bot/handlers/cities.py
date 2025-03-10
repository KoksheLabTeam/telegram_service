from aiogram import Router, F, types
import aiohttp
from app.bot.config import API_URL
from app.bot.handlers.start import get_main_keyboard
from app.bot.handlers.utils import api_request

router = Router()

@router.message(F.text == "Города")
async def list_cities(message: types.Message):
    telegram_id = message.from_user.id
    try:
        cities = await api_request("GET", f"{API_URL}city/", telegram_id)
        response = "\n".join([f"{city['id']}: {city['name']}" for city in cities])
        await message.answer(f"Доступные города:\n{response}", reply_markup=get_main_keyboard())
    except Exception as e:
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())