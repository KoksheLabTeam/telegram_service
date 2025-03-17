from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL
import logging

router = Router()
logger = logging.getLogger(__name__)

class CreateOrderStates(StatesGroup):
    title = State()
    description = State()
    price = State()
    due_date = State()
    category = State()

async def start_create_order(message: Message):
    await message.answer("Введите название заказа:")
    await message.bot.get_state(message.from_user.id, message.chat.id).set_state(CreateOrderStates.title)

@router.message(CreateOrderStates.title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await message.answer("Введите описание заказа (или пропустите, нажав Enter):")
    await state.set_state(CreateOrderStates.description)

# Добавьте остальные состояния для создания заказа...