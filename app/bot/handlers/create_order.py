from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from app.core.services.order import create_order
from app.core.schemas.order import OrderCreate
from app.core.models.user import User
from app.bot.handlers.utils import get_db_session, get_user_telegram_id
from .start import get_main_keyboard
from ..config import ADMIN_TELEGRAM_ID

router = Router()

class OrderCreation(StatesGroup):
    title = State()
    description = State()
    price = State()
    due_date = State()

@router.message(F.text == "Создать заказ")
async def start_order_creation(message: Message, state: FSMContext):
    telegram_id = get_user_telegram_id(message)
    session = next(get_db_session())
    user = session.query(User).filter(User.telegram_id == telegram_id).first()
    if not user or not user.is_customer:
        await message.answer("Только заказчики могут создавать заказы.", reply_markup=get_main_keyboard())
        return
    await message.answer("Введите название заказа:")
    await state.set_state(OrderCreation.title)

@router.message(OrderCreation.title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите описание заказа:")
    await state.set_state(OrderCreation.description)

@router.message(OrderCreation.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите желаемую цену (в тенге, например, 5000):")
    await state.set_state(OrderCreation.price)

@router.message(OrderCreation.price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
        await state.update_data(price=price)
        await message.answer("Введите срок выполнения (например, 2025-03-20):")
        await state.set_state(OrderCreation.due_date)
    except ValueError:
        await message.answer("Пожалуйста, введите корректную цену (число).")

@router.message(OrderCreation.due_date)
async def process_due_date(message: Message, state: FSMContext):
    data = await state.get_data()
    telegram_id = get_user_telegram_id(message)
    session = next(get_db_session())
    try:
        due_date = message.text  # Предполагаем формат YYYY-MM-DD, можно добавить валидацию
        order_data = OrderCreate(
            category_id=1,  # Захардкодим, можно добавить выбор категории
            title=data["title"],
            description=data["description"],
            desired_price=data["price"],
            due_date=due_date
        )
        order = create_order(session, order_data, telegram_id)
        roles = {
            "is_admin": telegram_id == ADMIN_TELEGRAM_ID,
            "is_executor": False,
            "is_customer": True
        }
        await message.answer(f"Заказ создан с ID: {order.id}", reply_markup=get_main_keyboard(roles))
    except Exception as e:
        await message.answer(f"Ошибка создания заказа: {e}", reply_markup=get_main_keyboard())
    await state.clear()