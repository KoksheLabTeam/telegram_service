from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.bot.config import ADMIN_TELEGRAM_ID
from ..common.profile import get_main_keyboard

router = Router()

@router.callback_query(F.data.startswith("complete_order_"))
async def complete_order(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    user = await api_request("GET", "user/me", telegram_id)
    if not user["is_executor"]:
        await callback.message.answer("Только исполнители могут завершать заказы.")
        await callback.answer()
        return
    try:
        order_id = int(callback.data.split("_")[2])
        order = await api_request("GET", f"order/{order_id}", telegram_id)
        if order["executor_id"] != user["id"]:
            await callback.message.answer("Вы не являетесь исполнителем этого заказа.")
            await callback.answer()
            return
        await api_request("PATCH", f"order/{order_id}", telegram_id, data={"status": "Выполнен"})
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": user["is_executor"], "is_customer": user["is_customer"]}
        await callback.message.answer("Заказ успешно завершён!", reply_markup=get_main_keyboard(roles))
    except Exception as e:
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": False}
        await callback.message.answer(f"Ошибка при завершении заказа: {e}", reply_markup=get_main_keyboard(roles))
    await callback.answer()