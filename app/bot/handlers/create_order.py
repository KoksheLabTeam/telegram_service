from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.config import API_URL
from app.bot.handlers.utils import api_request, get_user_telegram_id
from datetime import datetime, timedelta

router = Router()

def get_main_keyboard():
    from .start import get_main_keyboard
    return get_main_keyboard()

# Определяем состояния для FSM
class CreateOrder(StatesGroup):
    category = State()  # Выбор категории
    title = State()     # Название заказа
    description = State()  # Описание
    price = State()     # Желаемая цена
    due_date = State()  # Срок выполнения

@router.message(F.text == "Создать заказ")
async def start_create_order(message: Message, state: FSMContext):
    telegram_id = get_user_telegram_id(message)
    try:
        categories = await api_request("GET", f"{API_URL}category/", telegram_id)
        if not categories:
            await message.answer("В системе нет категорий. Обратитесь к администратору.", reply_markup=get_main_keyboard())
            return
        # Пока используем только первую категорию для простоты
        await state.update_data(category_id=categories[0]["id"])
        await message.answer("Введите название заказа:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        ))
        await state.set_state(CreateOrder.title)
    except Exception as e:
        await message.answer(f"Ошибка при загрузке категорий: {e}", reply_markup=get_main_keyboard())

@router.message(CreateOrder.title, F.text != "Отмена")
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите описание заказа (или напишите 'нет', чтобы пропустить):")
    await state.set_state(CreateOrder.description)

@router.message(CreateOrder.title, F.text == "Отмена")
async def cancel_order_creation(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Создание заказа отменено.", reply_markup=get_main_keyboard())

@router.message(CreateOrder.description, F.text != "Отмена")
async def process_description(message: Message, state: FSMContext):
    description = message.text if message.text.lower() != "нет" else None
    await state.update_data(description=description)
    await message.answer("Введите желаемую цену (в тенге, например, 5000):")
    await state.set_state(CreateOrder.price)

@router.message(CreateOrder.description, F.text == "Отмена")
async def cancel_order_creation(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Создание заказа отменено.", reply_markup=get_main_keyboard())

@router.message(CreateOrder.price, F.text != "Отмена")
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
        await state.update_data(desired_price=price)
        await message.answer("Введите срок выполнения (в формате ДД.ММ.ГГГГ, например, 20.03.2025):")
        await state.set_state(CreateOrder.due_date)
    except ValueError:
        await message.answer("Пожалуйста, введите корректную цену (число).")

@router.message(CreateOrder.price, F.text == "Отмена")
async def cancel_order_creation(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Создание заказа отменено.", reply_markup=get_main_keyboard())

@router.message(CreateOrder.due_date, F.text != "Отмена")
async def process_due_date(message: Message, state: FSMContext):
    try:
        due_date = datetime.strptime(message.text, "%d.%m.%Y")
        if due_date < datetime.now():
            raise ValueError("Срок выполнения не может быть в прошлом")
        telegram_id = get_user_telegram_id(message)
        data = await state.get_data()
        order_data = {
            "category_id": data["category_id"],
            "title": data["title"],
            "description": data["description"],
            "desired_price": data["desired_price"],
            "due_date": due_date.isoformat()
        }
        await api_request("POST", f"{API_URL}order/", telegram_id, data=order_data)
        await message.answer("Заказ успешно создан!", reply_markup=get_main_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите дату в формате ДД.ММ.ГГГГ и убедитесь, что она в будущем.")
    except Exception as e:
        await message.answer(f"Ошибка создания заказа: {e}", reply_markup=get_main_keyboard())
        await state.clear()

@router.message(CreateOrder.due_date, F.text == "Отмена")
async def cancel_order_creation(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Создание заказа отменено.", reply_markup=get_main_keyboard())