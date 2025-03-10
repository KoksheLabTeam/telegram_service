from aiogram import Router, F, types
from app.bot.handlers.start import get_main_keyboard
from app.bot.handlers.utils import api_request
from app.bot.config import API_URL

router = Router()

@router.message(F.text == "Список заказов")
async def list_orders(message: types.Message):
    telegram_id = message.from_user.id
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        if not orders:
            await message.answer("У вас нет заказов.", reply_markup=get_main_keyboard())
            return
        response = "\n".join([f"Заказ {order['id']}: {order['title']}" for order in orders])
        await message.answer(f"Ваши заказы:\n{response}", reply_markup=get_main_keyboard())
    except Exception as e:
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())