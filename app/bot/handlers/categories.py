from aiogram import Router, F, types
import aiohttp
from app.bot.config import API_URL
from app.bot.handlers.start import get_main_keyboard
from app.bot.handlers.utils import api_request

router = Router()

@router.message(F.text == "Категории")
async def list_categories(message: types.Message):
    telegram_id = message.from_user.id
    try:
        categories = await api_request("GET", f"{API_URL}category/", telegram_id)
        response = "\n".join([f"{cat['id']}: {cat['name']}" for cat in categories])
        await message.answer(f"Доступные категории:\n{response}", reply_markup=get_main_keyboard())
    except Exception as e:
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())