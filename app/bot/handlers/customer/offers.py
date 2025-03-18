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

@router.callback_query(ManageOffersStates.select_order, F.data.startswith("view_offers_"))
async def show_offers(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    order_id = int(callback.data.split("_")[-1])
    try:
        offers = await api_request("GET", f"{API_URL}order/{order_id}/offers", telegram_id)
        if not offers:
            await callback.message.edit_text("По этому заказу нет предложений.", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
            await state.clear()
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Цена: {offer['price']} тг, Время: {offer['estimated_time']} ч",
                                  callback_data=f"offer_{offer['id']}")]
            for offer in offers
        ] + [[InlineKeyboardButton(text="Назад", callback_data="back")]])
        await callback.message.edit_text("Предложения по заказу:", reply_markup=keyboard)
    except Exception as e:
        await callback.message.edit_text(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()
    await callback.answer()

@router.callback_query(ManageOffersStates.select_order, F.data.startswith("offer_"))
async def manage_offer(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    offer_id = int(callback.data.split("_")[-1])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Принять", callback_data=f"accept_{offer_id}"),
         InlineKeyboardButton(text="Отклонить", callback_data=f"reject_{offer_id}")],
        [InlineKeyboardButton(text="Назад", callback_data="back")]
    ])
    await callback.message.edit_text("Выберите действие с предложением:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(ManageOffersStates.select_order, F.data.startswith("accept_"))
async def accept_offer(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    offer_id = int(callback.data.split("_")[-1])
    try:
        order = await api_request("POST", f"{API_URL}offer/{offer_id}/offers/{offer_id}/accept", telegram_id)
        await callback.message.edit_text(f"Предложение принято, заказ ID {order['id']} в прогрессе!",
                                         reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()
    except Exception as e:
        await callback.message.edit_text(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()
    await callback.answer()

@router.callback_query(ManageOffersStates.select_order, F.data.startswith("reject_"))
async def reject_offer(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    offer_id = int(callback.data.split("_")[-1])
    try:
        await api_request("POST", f"{API_URL}offer/{offer_id}/offers/{offer_id}/reject", telegram_id)
        await callback.message.edit_text("Предложение отклонено.", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()
    except Exception as e:
        await callback.message.edit_text(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()
    await callback.answer()

@router.callback_query(ManageOffersStates.select_order, F.data == "back")
async def back_to_orders(callback: CallbackQuery, state: FSMContext):
    await manage_offers(callback.message, state)
    await callback.answer()

@router.callback_query(ManageOffersStates.select_order, F.data == "cancel")
async def cancel_offers(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Действие отменено.", reply_markup=get_main_keyboard(await get_user_roles(callback.from_user.id)))
    await state.clear()
    await callback.answer()