from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.bot.config import ADMIN_TELEGRAM_ID
from ..common.profile import get_main_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)

class OrderCreation(StatesGroup):
    title = State()
    description = State()
    category = State()
    price = State()
    due_date = State()

@router.message(F.text == "Создать заказ")
async def start_create_order(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    try:
        user = await api_request("GET", "user/me", telegram_id)
        if not user["is_customer"]:
            await message.answer("Только заказчики могут создавать заказы.", reply_markup=get_main_keyboard({"is_customer": False}))
            return
        await message.answer("Введите название заказа:")
        await state.set_state(OrderCreation.title)
    except Exception as e:
        logger.error(f"Ошибка в start_create_order: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard({"is_customer": False}))

@router.message(OrderCreation.title)
async def process_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if not title:
        await message.answer("Название заказа не может быть пустым. Введите название:")
        return
    await state.update_data(title=title)
    await message.answer("Введите описание заказа (или пропустите, отправив '-'):")
    await state.set_state(OrderCreation.description)

@router.message(OrderCreation.description)
async def process_description(message: Message, state: FSMContext):
    description = message.text.strip()
    await state.update_data(description=None if description == "-" else description)
    try:
        categories = await api_request("GET", "category/", await get_user_telegram_id(message))
        if not categories:
            await message.answer("В системе нет категорий. Обратитесь к администратору.")
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=cat["name"], callback_data=f"cat_{cat['id']}")] for cat in categories
        ] + [[InlineKeyboardButton(text="Готово", callback_data="category_done")]])
        await message.answer("Выберите категорию:", reply_markup=keyboard)
        await state.set_state(OrderCreation.category)
    except Exception as e:
        logger.error(f"Ошибка в process_description: {e}")
        await message.answer(f"Ошибка загрузки категорий: {e}", reply_markup=get_main_keyboard({"is_customer": True}))
        await state.clear()

@router.callback_query(F.data.startswith("cat_"), OrderCreation.category)
async def process_category(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[1])
    await state.update_data(category_id=category_id)
    await callback.message.edit_text(
        f"Вы выбрали категорию. Нажмите 'Готово', чтобы продолжить.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Готово", callback_data="category_done")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "category_done", OrderCreation.category)
async def category_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "category_id" not in data:
        await callback.message.edit_text("Вы не выбрали категорию. Пожалуйста, выберите категорию:")
        categories = await api_request("GET", "category/", callback.from_user.id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=cat["name"], callback_data=f"cat_{cat['id']}")] for cat in categories
        ] + [[InlineKeyboardButton(text="Готово", callback_data="category_done")]])
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()
        return
    await callback.message.edit_text("Введите желаемую цену (в тенге):")
    await state.set_state(OrderCreation.price)
    await callback.answer()

@router.message(OrderCreation.price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
        await state.update_data(desired_price=price)
        await message.answer("Введите срок выполнения (в формате ГГГГ-ММ-ДД):")
        await state.set_state(OrderCreation.due_date)
    except ValueError as e:
        await message.answer(f"Ошибка: {e}. Введите корректную цену (например, 5000):")
    except Exception as e:
        logger.error(f"Ошибка в process_price: {e}")
        await message.answer(f"Ошибка: {e}. Введите корректную цену.")

@router.message(OrderCreation.due_date)
async def process_due_date(message: Message, state: FSMContext):
    telegram_id = await get_user_telegram_id(message)
    try:
        from datetime import datetime
        due_date = datetime.strptime(message.text.strip(), "%Y-%m-%d")
        if due_date < datetime.utcnow():
            raise ValueError("Срок не может быть в прошлом")
        order_data = await state.get_data()
        order_data["due_date"] = due_date.isoformat()
        order = await api_request("POST", "order/", telegram_id, data=order_data)
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_customer": True}
        await message.answer(f"Заказ '{order['title']}' создан!", reply_markup=get_main_keyboard(roles))
        await state.clear()
    except ValueError as e:
        await message.answer(f"Ошибка: {e}. Введите дату в формате ГГГГ-ММ-ДД (например, 2025-03-20):")
    except Exception as e:
        logger.error(f"Ошибка в process_due_date: {e}")
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_customer": True}
        await message.answer(f"Ошибка создания заказа: {e}", reply_markup=get_main_keyboard(roles))
        await state.clear()