from aiogram import Router, types
from aiogram.filters import Text
import aiohttp
from app.bot.config import API_URL
from app.bot.handlers.start import main_keyboard

router = Router()

async def get_user_telegram_id(message: types.Message) -> int:
    return message.from_user.id

@router.message(Text("Список заказов"))
async def list_orders(message: types.Message):
    telegram_id = await get_user_telegram_id(message)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_URL}order/",
            headers={"x-telegram-id": str(telegram_id)}
        ) as resp:
            if resp.status == 200:
                orders = await resp.json()
                if orders:
                    response = "\n".join([f"Заказ {order['id']}: {order['title']} - {order['desiredPrice']} руб." for order in orders])
                    await message.reply(f"Ваши заказы:\n{response}", reply_markup=main_keyboard)
                else:
                    await message.reply("У вас пока нет заказов.", reply_markup=main_keyboard)
            else:
                await message.reply(f"Ошибка при загрузке заказов: {await resp.text()}")