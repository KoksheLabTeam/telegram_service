from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL
import logging

router = Router()
logger = logging.getLogger(__name__)

class ManageOffersStates(StatesGroup):
    select_order = State()

@router.message(F.text == "Посмотреть предложения")
async def manage_offers(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        user = await api_request("GET", f"{API_URL}user/me", telegram_id)
        if not user["is_customer"]:
            roles = await get_user_roles(telegram_id)
            await message.answer("Только заказчики могут просматривать предложения.", reply_markup=get_main_keyboard(roles))
            return
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        if not orders:
            roles = await get_user_roles(telegram_id)
            await message.answer("У вас нет заказов.", reply_markup=get_main_keyboard(roles))
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"ID {order['id']} - {order['title']}", callback_data=f"view_offers_{order['id']}")]
            for order in orders
        ] + [[InlineKeyboardButton(text="Отмена", callback_data="cancel")]])
        await message.answer("Выберите заказ для просмотра предложений:", reply_markup=keyboard)
        await state.set_state(ManageOffersStates.select_order)
    except Exception as e:
        roles = await get_user_roles(telegram_id)
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))