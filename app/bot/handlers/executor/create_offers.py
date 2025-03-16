from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.bot.config import ADMIN_TELEGRAM_ID, API_URL
from ..common.profile import get_main_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)

class OfferCreation(StatesGroup):
    order_id = State()
    price = State()
    estimated_time = State()

@router.message(F.text == "Создать предложение")
async def start_create_offer(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    user = await api_request("GET", "user/me", telegram_id)
    if not user["is_executor"]:
        await message.answer("Только исполнители могут создавать предложения.", reply_markup=get_main_keyboard({"is_executor": False}))
        return
    orders = await api_request("GET", "order/available", telegram_id)
    if not orders:
        await message.answer("Нет доступных заказов.", reply_markup=get_main_keyboard({"is_executor": True}))
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{o['title']} (ID: {o['id']})", callback_data=f"offer_{o['id']}")] for o in orders
    ])
    await message.answer("Выберите заказ для предложения:", reply_markup=keyboard)
    await state.set_state(OfferCreation.order_id)

@router.callback_query(F.data.startswith("offer_"), OfferCreation.order_id)
async def process_order_id(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    await state.update_data(order_id=order_id)
    await callback.message.answer("Введите цену предложения (в тенге):")
    await state.set_state(OfferCreation.price)
    await callback.answer()

@router.message(OfferCreation.price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
        await state.update_data(price=price)
        await message.answer("Введите оценочное время выполнения (в часах):")
        await state.set_state(OfferCreation.estimated_time)
    except ValueError as e:
        await message.answer(f"Ошибка: {e}. Введите корректную цену.")

@router.message(OfferCreation.estimated_time)
async def process_estimated_time(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    try:
        estimated_time = int(message.text.strip())
        if estimated_time <= 0:
            raise ValueError("Время должно быть положительным")
        offer_data = await state.get_data()
        offer_data["estimated_time"] = estimated_time
        offer = await api_request("POST", "offer/", telegram_id, data=offer_data)
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": True}
        await message.answer(f"Предложение для заказа ID {offer['order_id']} создано!", reply_markup=get_main_keyboard(roles))
    except ValueError as e:
        await message.answer(f"Ошибка: {e}. Введите корректное время.")
    except Exception as e:
        await message.answer(f"Ошибка создания предложения: {e}", reply_markup=get_main_keyboard({"is_executor": True}))
    await state.clear()