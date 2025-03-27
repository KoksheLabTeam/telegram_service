from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL
from datetime import datetime, timedelta
import logging

router = Router()
logger = logging.getLogger(__name__)

# Определяем состояния для управления заказами
class OrderStates(StatesGroup):
    select_order_to_cancel = State()
    select_order_to_edit = State()
    title = State()
    description = State()
    desired_price = State()
    due_date = State()
    category = State()

# Определяем состояния для создания заказа
class CreateOrderStates(StatesGroup):
    title = State()
    description = State()
    desired_price = State()
    due_date = State()
    category = State()

# Начало процесса создания заказа
@router.message(F.text == "Создать заказ")
async def start_create_order(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer("Только заказчики могут создавать заказы.", reply_markup=get_main_keyboard(roles))
        return
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

@router.message(CreateOrderStates.desired_price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        if price <= 0:
            await message.answer("Цена должна быть больше 0.")
            return
        await state.update_data(desired_price=price)
        await message.answer("Введите дедлайн (в формате ГГГГ-ММ-ДД ЧЧ:ММ):")
        await state.set_state(CreateOrderStates.due_date)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для цены.")

@router.message(CreateOrderStates.due_date)
async def process_due_date(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        due_date_str = message.text.strip()
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d %H:%M")
        if due_date < datetime.utcnow():
            await message.answer("Дедлайн не может быть в прошлом.")
            return
        await state.update_data(due_date=due_date.isoformat())
        categories = await api_request("GET", f"{API_URL}category/", telegram_id)
        if not categories:
            await message.answer("В системе нет категорий. Обратитесь к администратору.")
            await state.clear()
            return
        categories_list = "\n".join([f"ID: {cat['id']} - {cat['name']}" for cat in categories])
        await message.answer(f"Выберите категорию:\n{categories_list}\n\nВведите ID категории:")
        await state.set_state(CreateOrderStates.category)
    except ValueError:
        await message.answer("Пожалуйста, введите дату в формате ГГГГ-ММ-ДД ЧЧ:ММ (например, 2025-12-31 23:59).")

@router.message(CreateOrderStates.category)
async def process_category(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
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
        logger.info(f"Заказ ID {order['id']} успешно создан пользователем {telegram_id}")
        await message.answer(
            f"Заказ '{order['title']}' (ID: {order['id']}) успешно создан!\nВыберите действие в меню ниже:",
            reply_markup=get_main_keyboard(roles)
        )
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID категории.")
    except Exception as e:
        logger.error(f"Ошибка при создании заказа: {e}")
        await message.answer(
            f"Ошибка при создании заказа: {e}\nВыберите действие в меню ниже:",
            reply_markup=get_main_keyboard(roles)
        )
        await state.clear()

# Начало процесса отмены заказа
@router.message(F.text == "Отменить заказ")
async def start_cancel_order(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"] and not roles["is_admin"]:
        await message.answer("Только заказчики или администраторы могут отменять заказы.", reply_markup=get_main_keyboard(roles))
        return
    try:
        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
        user_id = user["id"]
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        logger.info(f"Полученные заказы для пользователя {telegram_id}: {orders}")
        now = datetime.utcnow()
        cancellable_orders = [
            o for o in orders
            if (o["status"] == "PENDING" and o["customer_id"] == user_id and
                (roles["is_admin"] or datetime.fromisoformat(o["created_at"].replace("Z", "+00:00")) + timedelta(minutes=30) > now))
        ]
        logger.info(f"Доступные для отмены заказы: {cancellable_orders}")
        if not cancellable_orders:
            await message.answer("У вас нет заказов, доступных для отмены.", reply_markup=get_main_keyboard(roles))
            return
        response = "Ваши заказы, доступные для отмены:\n\n"
        for order in cancellable_orders:
            response += f"ID: {order['id']} - {order['title']} (Создан: {order['created_at']})\n"
        await message.answer(response + "\nВведите ID заказа для отмены:")
        await state.set_state(OrderStates.select_order_to_cancel)
    except Exception as e:
        logger.error(f"Ошибка при загрузке заказов для отмены: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

# Обработка выбора заказа для отмены
@router.message(OrderStates.select_order_to_cancel)
async def process_cancel_order(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    try:
        order_id = int(message.text.strip())
        await api_request("POST", f"{API_URL}order/{order_id}/cancel", telegram_id)
        logger.info(f"Заказ ID {order_id} успешно отменён пользователем {telegram_id}")
        await message.answer(f"Заказ ID {order_id} успешно отменён!", reply_markup=get_main_keyboard(roles))
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
    except Exception as e:
        logger.error(f"Ошибка при отмене заказа: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))
        await state.clear()

# Начало процесса редактирования заказа
@router.message(F.text == "Редактировать заказ")
async def edit_order_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer("Только заказчики могут редактировать заказы.", reply_markup=get_main_keyboard(roles))
        return
    try:
        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
        user_id = user["id"]
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        now = datetime.utcnow()
        editable_orders = [
            o for o in orders
            if o["status"] == "PENDING" and o["customer_id"] == user_id and
            datetime.fromisoformat(o["created_at"].replace("Z", "+00:00")) + timedelta(minutes=30) > now
        ]
        if not editable_orders:
            await message.answer("У вас нет заказов, доступных для редактирования.", reply_markup=get_main_keyboard(roles))
            return
        response = "Выберите заказ для редактирования:\n\n"
        for order in editable_orders:
            response += f"ID: {order['id']} - {order['title']} (Создан: {order['created_at']})\n"
        await message.answer(response + "\nВведите ID заказа:")
        await state.set_state(OrderStates.select_order_to_edit)
    except Exception as e:
        logger.error(f"Ошибка при загрузке заказов для редактирования: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

# Обработка выбора заказа для редактирования
@router.message(OrderStates.select_order_to_edit)
async def process_edit_order(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    try:
        order_id = int(message.text.strip())
        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
        user_id = user["id"]
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        order = next(
            (o for o in orders
             if o["id"] == order_id and o["status"] == "PENDING" and o["customer_id"] == user_id and
             datetime.fromisoformat(o["created_at"].replace("Z", "+00:00")) + timedelta(minutes=30) > datetime.utcnow()),
            None
        )
        if not order:
            await message.answer("Заказ не найден или недоступен для редактирования.", reply_markup=get_main_keyboard(roles))
            await state.clear()
            return
        await state.update_data(
            order_id=order_id,
            title=order["title"],
            description=order["description"],
            desired_price=order["desired_price"],
            due_date=order["due_date"],
            category_id=order["category_id"]
        )
        await message.answer("Введите новое название заказа (или нажмите Enter для сохранения текущего):")
        await state.set_state(OrderStates.title)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
    except Exception as e:
        logger.error(f"Ошибка при выборе заказа для редактирования: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))
        await state.clear()

# Обработка редактирования полей
@router.message(OrderStates.title)
async def process_edit_title(message: Message, state: FSMContext):
    data = await state.get_data()
    new_title = message.text.strip() if message.text.strip() else data["title"]
    await state.update_data(title=new_title)
    await message.answer("Введите новое описание заказа (или нажмите Enter для сохранения текущего):")
    await state.set_state(OrderStates.description)

@router.message(OrderStates.description)
async def process_edit_description(message: Message, state: FSMContext):
    data = await state.get_data()
    new_description = message.text.strip() if message.text.strip() else data["description"]
    await state.update_data(description=new_description)
    await message.answer("Введите новую желаемую цену (в рублях, или нажмите Enter для сохранения текущей):")
    await state.set_state(OrderStates.desired_price)

@router.message(OrderStates.desired_price)
async def process_edit_price(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        new_price = float(message.text.strip()) if message.text.strip() else data["desired_price"]
        if new_price <= 0:
            await message.answer("Цена должна быть больше 0.")
            return
        await state.update_data(desired_price=new_price)
        await message.answer("Введите новый дедлайн (в формате ГГГГ-ММ-ДД ЧЧ:ММ, или нажмите Enter для сохранения текущего):")
        await state.set_state(OrderStates.due_date)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для цены.")

@router.message(OrderStates.due_date)
async def process_edit_due_date(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        data = await state.get_data()
        new_due_date_str = message.text.strip() if message.text.strip() else None
        if new_due_date_str:
            new_due_date = datetime.strptime(new_due_date_str, "%Y-%m-%d %H:%M")
            if new_due_date < datetime.utcnow():
                await message.answer("Дедлайн не может быть в прошлом.")
                return
            await state.update_data(due_date=new_due_date.isoformat())
        categories = await api_request("GET", f"{API_URL}category/", telegram_id)
        categories_list = "\n".join([f"ID: {cat['id']} - {cat['name']}" for cat in categories])
        await message.answer(f"Выберите новую категорию (или нажмите Enter для сохранения текущей):\n{categories_list}\n\nВведите ID категории:")
        await state.set_state(OrderStates.category)
    except ValueError:
        await message.answer("Пожалуйста, введите дату в формате ГГГГ-ММ-ДД ЧЧ:ММ (например, 2025-12-31 23:59).")

@router.message(OrderStates.category)
async def process_edit_category(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    try:
        data = await state.get_data()
        order_id = data["order_id"]
        new_category_id = int(message.text.strip()) if message.text.strip() else data["category_id"]
        order_data = {
            "title": data["title"],
            "description": data["description"],
            "desired_price": data["desired_price"],
            "due_date": data["due_date"],
            "category_id": new_category_id
        }
        # Удаляем None значения, чтобы не перезаписывать существующие поля
        order_data = {k: v for k, v in order_data.items() if v is not None}
        await api_request("PATCH", f"{API_URL}order/{order_id}", telegram_id, data=order_data)
        logger.info(f"Заказ ID {order_id} успешно отредактирован пользователем {telegram_id}")
        await message.answer(
            f"Заказ ID {order_id} успешно отредактирован!\nВыберите действие в меню ниже:",
            reply_markup=get_main_keyboard(roles)
        )
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID категории.")
    except Exception as e:
        logger.error(f"Ошибка при редактировании заказа: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))
        await state.clear()