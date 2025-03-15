from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.core.services.offer import create_offer
from app.core.schemas.offer import OfferCreate
from app.core.services.order import get_available_orders
from app.core.models.user import User
from app.bot.handlers.utils import get_db_session, get_user_telegram_id
from .start import get_main_keyboard
from datetime import datetime

router = Router()

class CreateOffer(StatesGroup):
    select_order = State()
    price = State()
    estimated_time = State()

@router.message(F.text == "Создать предложение")
async def start_create_offer(message: Message, state: FSMContext):
    telegram_id = get_user_telegram_id(message)
    session = next(get_db_session())
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user or not user.is_executor:
            await message.answer("Только исполнители могут создавать предложения.", reply_markup=get_main_keyboard())
            return
        orders = get_available_orders(session)
        if not orders:
            await message.answer("Нет доступных заказов для предложений.", reply_markup=get_main_keyboard({"is_executor": True}))
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"ID {order.id} - {order.title}", callback_data=f"offer_order_{order.id}")]
            for order in orders
        ] + [[InlineKeyboardButton(text="Отмена", callback_data="cancel")]])
        await message.answer("Выберите заказ для предложения:", reply_markup=keyboard)
        await state.set_state(CreateOffer.select_order)
    except Exception as e:
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())

@router.callback_query(CreateOffer.select_order, F.data.startswith("offer_order_"))
async def process_order_selection(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    await state.update_data(order_id=order_id)
    await callback.message.answer("Введите вашу цену (в тенге, например, 6000):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    ))
    await state.set_state(CreateOffer.price)
    await callback.answer()

@router.callback_query(CreateOffer.select_order, F.data == "cancel")
async def cancel_offer_creation(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Создание предложения отменено.", reply_markup=get_main_keyboard({"is_executor": True}))
    await callback.answer()

@router.message(CreateOffer.price, F.text != "Отмена")
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
        await state.update_data(price=price)
        await message.answer("Введите оценочное время выполнения (в часах, например, 5):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        ))
        await state.set_state(CreateOffer.estimated_time)
    except ValueError:
        await message.answer("Пожалуйста, введите корректную цену (число).")

@router.message(CreateOffer.price, F.text == "Отмена")
async def cancel_offer_creation(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Создание предложения отменено.", reply_markup=get_main_keyboard({"is_executor": True}))

@router.message(CreateOffer.estimated_time, F.text != "Отмена")
async def process_estimated_time(message: Message, state: FSMContext):
    try:
        estimated_time = int(message.text)
        if estimated_time <= 0:
            raise ValueError("Время должно быть положительным")
        telegram_id = get_user_telegram_id(message)
        session = next(get_db_session())
        data = await state.get_data()
        offer_data = OfferCreate(
            order_id=data["order_id"],
            price=data["price"],
            estimated_time=estimated_time,
            start_date=datetime.utcnow()
        )
        create_offer(session, offer_data, telegram_id)
        await message.answer("Предложение успешно создано!", reply_markup=get_main_keyboard({"is_executor": True}))
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное время (целое число).")
    except Exception as e:
        await message.answer(f"Ошибка создания предложения: {e}", reply_markup=get_main_keyboard({"is_executor": True}))
    await state.clear()

@router.message(CreateOffer.estimated_time, F.text == "Отмена")
async def cancel_offer_creation(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Создание предложения отменено.", reply_markup=get_main_keyboard({"is_executor": True}))