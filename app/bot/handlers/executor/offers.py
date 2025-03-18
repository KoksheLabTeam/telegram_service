from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL
import logging

router = Router()
logger = logging.getLogger(__name__)

# Определяем состояния для создания предложения
class CreateOfferStates(StatesGroup):
    order_id = State()
    price = State()
    description = State()

async def start_create_offer(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        if not orders:
            await message.answer(
                "Нет доступных заказов для создания предложения.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
            return
        orders_list = "\n".join([f"ID: {order['id']} - {order['title']}" for order in orders])
        await message.answer(f"Доступные заказы:\n{orders_list}\n\nВведите ID заказа:")
        await state.set_state(CreateOfferStates.order_id)
    except Exception as e:
        logger.error(f"Ошибка при загрузке заказов: {e}")
        await message.answer(
            f"Ошибка: {e}",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()

@router.message(CreateOfferStates.order_id)
async def process_order_id(message: Message, state: FSMContext):
    try:
        order_id = int(message.text.strip())
        await state.update_data(order_id=order_id)
        await message.answer("Введите вашу цену за выполнение (в рублях):")
        await state.set_state(CreateOfferStates.price)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")

@router.message(CreateOfferStates.price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        await state.update_data(price=price)
        await message.answer("Введите описание вашего предложения:")
        await state.set_state(CreateOfferStates.description)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для цены.")

@router.message(CreateOfferStates.description)
async def process_description(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        description = message.text.strip()
        data = await state.get_data()
        offer_data = {
            "order_id": data["order_id"],
            "price": data["price"],
            "description": description
        }
        offer = await api_request("POST", f"{API_URL}offer/", telegram_id, data=offer_data)
        await message.answer(
            f"Предложение для заказа ID {offer['order_id']} успешно создано!\nВыберите действие в меню ниже:",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при создании предложения: {e}")
        await message.answer(
            f"Ошибка при создании предложения: {e}\nВыберите действие в меню ниже:",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()