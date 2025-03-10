from aiogram import Router, types
from aiogram.filters import Text
import aiohttp
from app.bot.config import API_URL
from app.bot.handlers.start import main_keyboard

router = Router()

async def get_user_telegram_id(message: types.Message) -> int:
    return message.from_user.id

@router.message(Text("Сменить роль"))
async def switch_role(message: types.Message):
    telegram_id = await get_user_telegram_id(message)
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}user/switch-role",
            headers={"x-telegram-id": str(telegram_id)}
        ) as resp:
            if resp.status == 200:
                user = await resp.json()
                new_role = "заказчик" if user["isCustomer"] else "исполнитель"
                await message.reply(f"Ваша роль изменена на: {new_role}", reply_markup=main_keyboard)
            else:
                await message.reply(f"Ошибка при смене роли: {await resp.text()}")