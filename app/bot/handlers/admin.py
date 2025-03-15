from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.config import ADMIN_TELEGRAM_ID
from app.core.services.user import get_users, delete_user_by_id
from app.core.services.order import get_orders_by_user, delete_order_by_id
from app.core.services.city import create_city, get_all_cities, update_city_by_id, delete_city_by_id
from app.core.schemas.city import CityCreate, CityUpdate
from app.core.models.user import User
from app.core.models.order import Order
from app.bot.handlers.utils import get_db_session, get_user_telegram_id
from .start import get_main_keyboard

router = Router()

class AdminPanel(StatesGroup):
    delete_user = State()
    delete_order = State()
    add_city = State()
    edit_city = State()
    delete_city = State()

@router.message(F.text == "Админ-панель", lambda msg: msg.from_user.id == ADMIN_TELEGRAM_ID)
async def admin_panel(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Список пользователей", callback_data="list_users")],
        [InlineKeyboardButton(text="Список заказов", callback_data="list_orders")],
        [InlineKeyboardButton(text="Удалить пользователя", callback_data="delete_user")],
        [InlineKeyboardButton(text="Удалить заказ", callback_data="delete_order")],
        [InlineKeyboardButton(text="Добавить город", callback_data="add_city")],
        [InlineKeyboardButton(text="Изменить город", callback_data="edit_city")],
        [InlineKeyboardButton(text="Удалить город", callback_data="delete_city")],
        [InlineKeyboardButton(text="Назад", callback_data="back")]
    ])
    await message.answer("Админ-панель:", reply_markup=keyboard)

@router.callback_query(F.data == "list_users")
async def list_users(callback: CallbackQuery):
    session = next(get_db_session())
    try:
        users = get_users(session)
        if not users:
            await callback.message.answer("Пользователей нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return
        response = "Список пользователей:\n\n"
        for user in users:
            role = "Заказчик" if user.is_customer else "Исполнитель" if user.is_executor else "Не определена"
            response += (
                f"ID: {user.id}\n"
                f"Telegram ID: {user.telegram_id}\n"
                f"Имя: {user.name}\n"
                f"Роль: {role}\n"
                f"Рейтинг: {user.rating}\n\n"
            )
        await callback.message.answer(response.strip(), reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        await callback.message.answer(f"Ошибка загрузки пользователей: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.callback_query(F.data == "list_orders")
async def list_orders(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    session = next(get_db_session())
    try:
        orders = get_orders_by_user(session, telegram_id)
        if not orders:
            await callback.message.answer("Заказов нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return
        response = "Список заказов:\n\n"
        for order in orders:
            status_map = {
                "В_ожидании": "Ожидает",
                "В_прогрессе": "В процессе",
                "Выполнен": "Завершён",
                "Отменен": "Отменён"
            }
            status = status_map.get(order.status, order.status)
            due_date = order.due_date.strftime("%Y-%m-%d")
            response += (
                f"ID: {order.id}\n"
                f"Название: {order.title}\n"
                f"Статус: {status}\n"
                f"Желаемая цена: {order.desired_price} тенге\n"
                f"Срок: {due_date}\n\n"
            )
        await callback.message.answer(response.strip(), reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        await callback.message.answer(f"Ошибка загрузки заказов: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.callback_query(F.data == "delete_user")
async def start_delete_user(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID пользователя для удаления:")
    await state.set_state(AdminPanel.delete_user)
    await callback.answer()

@router.message(AdminPanel.delete_user)
async def process_delete_user(message: Message, state: FSMContext):
    session = next(get_db_session())
    try:
        user_id = int(message.text)
        delete_user_by_id(session, user_id)
        await message.answer(f"Пользователь с ID {user_id} удалён.", reply_markup=get_main_keyboard({"is_admin": True}))
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID (число).")
    except Exception as e:
        await message.answer(f"Ошибка удаления пользователя: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()

@router.callback_query(F.data == "delete_order")
async def start_delete_order(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID заказа для удаления:")
    await state.set_state(AdminPanel.delete_order)
    await callback.answer()

@router.message(AdminPanel.delete_order)
async def process_delete_order(message: Message, state: FSMContext):
    session = next(get_db_session())
    try:
        order_id = int(message.text)
        delete_order_by_id(session, order_id)
        await message.answer(f"Заказ с ID {order_id} удалён.", reply_markup=get_main_keyboard({"is_admin": True}))
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID (число).")
    except Exception as e:
        await message.answer(f"Ошибка удаления заказа: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()

@router.callback_query(F.data == "add_city")
async def start_add_city(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название нового города:")
    await state.set_state(AdminPanel.add_city)
    await callback.answer()

@router.message(AdminPanel.add_city)
async def process_add_city(message: Message, state: FSMContext):
    session = next(get_db_session())
    city_name = message.text.strip()
    try:
        city_data = CityCreate(name=city_name)
        create_city(session, city_data)
        await message.answer(f"Город '{city_name}' успешно добавлен.", reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        await message.answer(f"Ошибка добавления города: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()

@router.callback_query(F.data == "edit_city")
async def start_edit_city(callback: CallbackQuery, state: FSMContext):
    session = next(get_db_session())
    try:
        cities = get_all_cities(session)
        if not cities:
            await callback.message.answer("Городов нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return
        response = "Список городов:\n\n"
        for city in cities:
            response += f"ID: {city.id} - {city.name}\n"
        await callback.message.answer(response + "\nВведите ID города для изменения:")
        await state.set_state(AdminPanel.edit_city)
    except Exception as e:
        await callback.message.answer(f"Ошибка загрузки городов: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.message(AdminPanel.edit_city)
async def process_edit_city(message: Message, state: FSMContext):
    try:
        city_id = int(message.text)
        await state.update_data(city_id=city_id)
        await message.answer("Введите новое название города:")
        await state.set_state(AdminPanel.edit_city)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID (число).")
        await state.clear()

@router.message(AdminPanel.edit_city, lambda msg: "city_id" in (state.get_data(msg) or {}))
async def process_edit_city_name(message: Message, state: FSMContext):
    session = next(get_db_session())
    data = await state.get_data()
    city_id = data["city_id"]
    new_name = message.text.strip()
    try:
        city_update = CityUpdate(name=new_name)
        update_city_by_id(session, city_update, city_id)
        await message.answer(f"Город с ID {city_id} обновлён на '{new_name}'.", reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        await message.answer(f"Ошибка изменения города: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()

@router.callback_query(F.data == "delete_city")
async def start_delete_city(callback: CallbackQuery, state: FSMContext):
    session = next(get_db_session())
    try:
        cities = get_all_cities(session)
        if not cities:
            await callback.message.answer("Городов нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return
        response = "Список городов:\n\n"
        for city in cities:
            response += f"ID: {city.id} - {city.name}\n"
        await callback.message.answer(response + "\nВведите ID города для удаления:")
        await state.set_state(AdminPanel.delete_city)
    except Exception as e:
        await callback.message.answer(f"Ошибка загрузки городов: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.message(AdminPanel.delete_city)
async def process_delete_city(message: Message, state: FSMContext):
    session = next(get_db_session())
    try:
        city_id = int(message.text)
        delete_city_by_id(session, city_id)
        await message.answer(f"Город с ID {city_id} удалён.", reply_markup=get_main_keyboard({"is_admin": True}))
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID (число).")
    except Exception as e:
        await message.answer(f"Ошибка удаления города: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()

@router.callback_query(F.data == "back")
async def back_to_main(callback: CallbackQuery):
    await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()