from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL
import logging

router = Router()
logger = logging.getLogger(__name__)

# Определяем состояния для создания заказа
class CreateOrderStates(StatesGroup):
    title = State()
    description = State()
    desired_price = State()  # Используем desired_price вместо price
    due_date = State()
    category = State()

async def start_create_order(message: Message, state: FSMContext):
    await message.answer("Введите название заказа:")
    await state.set_state(CreateOrderStates.title)

@router.message(CreateOrderStates.title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await message.answer("Введите описание заказа:")
    await state.set_state(CreateOrderStates.description)

@router.message(CreateOrderStates.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await message.answer("Введите желаемую цену (в рублях):")
    await state.set_state(CreateOrderStates.desired_price)

@router.message(CreateOrderStates.desired_price)  # Исправлено с price на desired_price
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        await state.update_data(desired_price=price)
        await message.answer("Введите дедлайн (в формате ДД.ММ.ГГГГ):")
        await state.set_state(CreateOrderStates.due_date)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для цены.")

@router.message(CreateOrderStates.due_date)
async def process_due_date(message: Message, state: FSMContext):
    try:
        due_date = message.text.strip()
        # Проверка формата даты (можно усилить валидацию)
        datetime.strptime(due_date, "%d.%m.%Y")
        await state.update_data(due_date=due_date)
        telegram_id = message.from_user.id
        categories = await api_request("GET", f"{API_URL}category/", telegram_id)
        if not categories:
            await message.answer("В системе нет категорий. Обратитесь к администратору.")
            await state.clear()
            return
        categories_list = "\n".join([f"ID: {cat['id']} - {cat['name']}" for cat in categories])
        await message.answer(f"Выберите категорию:\n{categories_list}\n\nВведите ID категории:")
        await state.set_state(CreateOrderStates.category)
    except ValueError:
        await message.answer("Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.")

@router.message(CreateOrderStates.category)
async def process_category(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        category_id = int(message.text.strip())
        data = await state.get_data()
        order_data = {
            "category_id": category_id,
            "title": data["title"],
            "description": data["description"],
            "desired_price": data["desired_price"],
            "due_date": data["due_date"]
        }
        order = await api_request("POST", f"{API_URL}order/", telegram_id, data=order_data)
        await message.answer(
            f"Заказ '{order['title']}' (ID: {order['id']}) успешно создан!\nВыберите действие в меню ниже:",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID категории.")
    except Exception as e:
        logger.error(f"Ошибка при создании заказа: {e}")
        await message.answer(
            f"Ошибка при создании заказа: {e}\nВыберите действие в меню ниже:",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()