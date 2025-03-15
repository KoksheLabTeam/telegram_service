from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.core.database.helper import SessionLocal
from app.core.services.order import create_order
from app.core.schemas.order import OrderCreate
import logging
from app.bot.config import ADMIN_TELEGRAM_ID, API_URL

router = Router()
logger = logging.getLogger(__name__)

def get_main_keyboard(roles: dict = None):
    from .start import get_main_keyboard
    return get_main_keyboard(roles)

class CreateOrder(StatesGroup):
    category = State()
    title = State()
    description = State()
    price = State()
    due_date = State()

@router.message(F.text == "Создать заказ")
async def start_create_order(message: Message, state: FSMContext):
    telegram_id = get_user_telegram_id(message)
    try:
        user = await api_request("GET", f"{API_URL}user/me", telegram_id)
        if not user["is_customer"]:
            await message.answer("Только заказчики могут создавать заказы.", reply_markup=get_main_keyboard())
            return
        categories = await api_request("GET", f"{API_URL}category/", telegram_id)
        if not categories:
            await message.answer("Категорий пока нет, обратитесь к администратору.", reply_markup=get_main_keyboard())
            return
        response = "Выберите категорию:\n\n"
        for i, category in enumerate(categories, 1):
            response += f"{i}. {category['name']}\n"
        await state.update_data(categories=categories)
        await message.answer(response.strip(), reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        ))
        await state.set_state(CreateOrder.category)
    except Exception as e:
        logger.error(f"Ошибка при загрузке категорий: {e}")
        await message.answer(f"Ошибка при загрузке категорий: {e}", reply_markup=get_main_keyboard())

@router.message(CreateOrder.category, F.text != "Отмена")
async def process_category(message: Message, state: FSMContext):
    try:
        category_idx = int(message.text) - 1
        data = await state.get_data()
        categories = data["categories"]
        if 0 <= category_idx < len(categories):
            category_id = categories[category_idx]["id"]
            await state.update_data(category_id=category_id)
            await message.answer("Введите название заказа:")
            await state.set_state(CreateOrder.title)
        else:
            await message.answer("Пожалуйста, выберите номер из списка.")
    except ValueError:
        await message.answer("Пожалуйста, введите номер категории.")

@router.message(CreateOrder.category, F.text == "Отмена")
async def cancel_order_creation(message: Message, state: FSMContext):
    logger.info("Создание заказа отменено пользователем")
    await state.clear()
    await message.answer("Создание заказа отменено.", reply_markup=get_main_keyboard())

@router.message(CreateOrder.title, F.text != "Отмена")
async def process_title(message: Message, state: FSMContext):
    logger.info(f"Пользователь ввёл название: {message.text}")
    await state.update_data(title=message.text)
    await message.answer("Введите описание заказа (или напишите 'нет', чтобы пропустить):")
    await state.set_state(CreateOrder.description)

@router.message(CreateOrder.title, F.text == "Отмена")
async def cancel_order_creation(message: Message, state: FSMContext):
    logger.info("Создание заказа отменено пользователем")
    await state.clear()
    await message.answer("Создание заказа отменено.", reply_markup=get_main_keyboard())

@router.message(CreateOrder.description, F.text != "Отмена")
async def process_description(message: Message, state: FSMContext):
    description = message.text if message.text.lower() != "нет" else None
    logger.info(f"Пользователь ввёл описание: {description}")
    await state.update_data(description=description)
    await message.answer("Введите желаемую цену (в тенге, например, 5000):")
    await state.set_state(CreateOrder.price)

@router.message(CreateOrder.description, F.text == "Отмена")
async def cancel_order_creation(message: Message, state: FSMContext):
    logger.info("Создание заказа отменено пользователем")
    await state.clear()
    await message.answer("Создание заказа отменено.", reply_markup=get_main_keyboard())

@router.message(CreateOrder.price, F.text != "Отмена")
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
        logger.info(f"Пользователь ввёл цену: {price}")
        await state.update_data(desired_price=price)
        await message.answer("Введите срок выполнения (в формате ДД.ММ.ГГГГ, например, 20.03.2025):")
        await state.set_state(CreateOrder.due_date)
    except ValueError as e:
        logger.warning(f"Некорректная цена: {e}")
        await message.answer("Пожалуйста, введите корректную цену (число).")

@router.message(CreateOrder.price, F.text == "Отмена")
async def cancel_order_creation(message: Message, state: FSMContext):
    logger.info("Создание заказа отменено пользователем")
    await state.clear()
    await message.answer("Создание заказа отменено.", reply_markup=get_main_keyboard())

@router.message(CreateOrder.due_date, F.text != "Отмена")
async def process_due_date(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    logger.info(f"Пользователь {telegram_id} ввёл срок выполнения: {message.text}")
    try:
        due_date = datetime.strptime(message.text, "%d.%m.%Y")
        if due_date < datetime.now():
            raise ValueError("Срок выполнения не может быть в прошлом")
        data = await state.get_data()
        order_data = OrderCreate(
            category_id=data["category_id"],
            title=data["title"],
            description=data["description"],
            desired_price=data["desired_price"],
            due_date=due_date
        )
        logger.info(f"Создание заказа с данными: {order_data}")
        with SessionLocal() as session:
            user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
            order = create_order(session, order_data, user["id"])  # Используем user["id"] вместо telegram_id
            logger.info(f"Заказ успешно создан: ID {order.id}")
            roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": user["is_executor"], "is_customer": user["is_customer"]}
            await message.answer(f"Заказ успешно создан! ID: {order.id}", reply_markup=get_main_keyboard(roles))
        await state.clear()
    except ValueError as ve:
        logger.warning(f"Ошибка в формате даты или дата в прошлом: {ve}")
        await message.answer(f"Пожалуйста, введите дату в формате ДД.ММ.ГГГГ и убедитесь, что она в будущем: {ve}")
    except Exception as e:
        logger.error(f"Ошибка создания заказа: {e}")
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": True}
        await message.answer(f"Ошибка создания заказа: {e}", reply_markup=get_main_keyboard(roles))
        await state.clear()

@router.message(CreateOrder.due_date, F.text == "Отмена")
async def cancel_order_creation(message: Message, state: FSMContext):
    logger.info("Создание заказа отменено пользователем")
    await state.clear()
    await message.answer("Создание заказа отменено.", reply_markup=get_main_keyboard())

