from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp
from app.bot.config import API_URL

async def get_user_telegram_id(message: types.Message) -> int:
    return message.from_user.id

async def api_request(method: str, url: str, telegram_id: int, json=None):
    async with aiohttp.ClientSession() as session:
        async with session.request(
            method=method,
            url=url,
            json=json,
            headers={"x-telegram-id": str(telegram_id)}
        ) as resp:
            if resp.status in [200, 201, 204]:
                if resp.status == 204:
                    return None
                return await resp.json()
            else:
                raise Exception(f"Ошибка API: {await resp.text()} (Статус: {resp.status})")

def create_back_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="Назад", callback_data="back"))
    return keyboard

def create_categories_keyboard(categories: list) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    for category in categories:
        keyboard.add(InlineKeyboardButton(
            text=category["name"],
            callback_data=f"category_{category['id']}"
        ))
    keyboard.add(InlineKeyboardButton(text="Назад", callback_data="back"))
    return keyboard

def create_cities_keyboard(cities: list) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    for city in cities:
        keyboard.add(InlineKeyboardButton(
            text=city["name"],
            callback_data=f"city_{city['id']}"
        ))
    keyboard.add(InlineKeyboardButton(text="Назад", callback_data="back"))
    return keyboard