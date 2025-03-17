from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.config import ADMIN_TELEGRAM_ID, API_URL
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.bot.handlers.start import get_main_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)

class AdminPanel(StatesGroup):
    delete_user = State()
    delete_order = State()
    add_city = State()
    edit_city = State()
    delete_city = State()

@router.message(F.text == "Админ панель")
async def admin_panel(message: Message):
    logger.info(f"Попытка доступа к админ-панели от пользователя {message.from_user.id}")
    if message.from_user.id != ADMIN_TELEGRAM_ID:
        logger.warning(f"Доступ запрещен для пользователя {message.from_user.id}")
        await message.answer("Доступ запрещен!")
        return
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
    logger.info(f"Обработчик list_users вызван для telegram_id={callback.from_user.id}")
    telegram_id = callback.from_user.id
    try:
        users = await api_request("GET", f"{API_URL}user/all", telegram_id)
        if not users:
            await callback.message.answer("Пользователей нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return

        response = "Список пользователей:\n\n"
        for user in users:
            role = "Заказчик" if user["is_customer"] else "Исполнитель" if user["is_executor"] else "Не определена"
            response += (
                f"ID: {user['id']}\n"
                f"Telegram ID: {user['telegram_id']}\n"
                f"Имя: {user['name']}\n"
                f"Роль: {role}\n"
                f"Рейтинг: {user['rating']}\n\n"
            )
        await callback.message.answer(response.strip(), reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        logger.error(f"Ошибка в list_users: {e}")
        await callback.message.answer(f"Ошибка загрузки пользователей: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.callback_query(F.data == "list_orders")
async def list_orders(callback: CallbackQuery):
    logger.info(f"Обработчик list_orders вызван для telegram_id={callback.from_user.id}")
    telegram_id = callback.from_user.id
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        if not orders:
            await callback.message.answer("Заказов нет.", reply_markup=get_main_keyboard({"is_admin": True}))
            await callback.answer()
            return

        response = "Список заказов:\n\n"
        status_map = {
            "В_ожидании": "Ожидает",
            "В_прогрессе": "В процессе",
            "Выполнен": "Завершён",
            "Отменен": "Отменён"
        }
        for order in orders:
            status = status_map.get(order["status"], order["status"])
            due_date = order["due_date"].split("T")[0]
            response += (
                f"ID: {order['id']}\n"
                f"Название: {order['title']}\n"
                f"Статус: {status}\n"
                f"Желаемая цена: {order['desired_price']} тенге\n"
                f"Срок: {due_date}\n\n"
            )
        await callback.message.answer(response.strip(), reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        logger.error(f"Ошибка в list_orders: {e}")
        await callback.message.answer(f"Ошибка загрузки заказов: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await callback.answer()

@router.callback_query(F.data == "delete_user")
async def start_delete_user(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Обработчик start_delete_user вызван для telegram_id={callback.from_user.id}")
    await callback.message.answer("Введите ID пользователя для удаления:")
    await state.set_state(AdminPanel.delete_user)
    await callback.answer()

@router.message(AdminPanel.delete_user)
async def process_delete_user(message: Message, state: FSMContext):
    logger.info(f"Обработчик process_delete_user вызван для telegram_id={message.from_user.id}")
    telegram_id = get_user_telegram_id(message)
    try:
        user_id = int(message.text)
        await api_request("DELETE", f"{API_URL}user/{user_id}", telegram_id)
        await message.answer(f"Пользователь с ID {user_id} удалён.", reply_markup=get_main_keyboard({"is_admin": True}))
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID (число).")
    except Exception as e:
        logger.error(f"Ошибка в process_delete_user: {e}")
        await message.answer(f"Ошибка удаления пользователя: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()

@router.callback_query(F.data == "delete_order")
async def start_delete_order(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Обработчик start_delete_order вызван для telegram_id={callback.from_user.id}")
    await callback.message.answer("Введите ID заказа для удаления:")
    await state.set_state(AdminPanel.delete_order)
    await callback.answer()

@router.message(AdminPanel.delete_order)
async def process_delete_order(message: Message, state: FSMContext):
    logger.info(f"Обработчик process_delete_order вызван для telegram_id={message.from_user.id}")
    telegram_id = get_user_telegram_id(message)
    try:
        order_id = int(message.text)
        await api_request("DELETE", f"{API_URL}order/{order_id}", telegram_id)
        await message.answer(f"Заказ с ID {order_id} удалён.", reply_markup=get_main_keyboard({"is_admin": True}))
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID (число).")
    except Exception as e:
        logger.error(f"Ошибка в process_delete_order: {e}")
        await message.answer(f"Ошибка удаления заказа: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()

@router.callback_query(F.data == "add_city")
async def start_add_city(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Обработчик start_add_city вызван для telegram_id={callback.from_user.id}")
    await callback.message.answer("Введите название города для добавления:")
    await state.set_state(AdminPanel.add_city)
    await callback.answer()

@router.message(AdminPanel.add_city)
async def process_add_city(message: Message, state: FSMContext):
    logger.info(f"Обработчик process_add_city вызван для telegram_id={message.from_user.id}")
    telegram_id = get_user_telegram_id(message)
    try:
        city_name = message.text.strip()
        if not city_name:
            await message.answer("Название города не может быть пустым.")
            return
        # Изменено json на data
        await api_request("POST", f"{API_URL}city/", telegram_id, data={"name": city_name})
        await message.answer(f"Город '{city_name}' добавлен.", reply_markup=get_main_keyboard({"is_admin": True}))
    except Exception as e:
        logger.error(f"Ошибка в process_add_city: {e}")
        await message.answer(f"Ошибка добавления города: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()

@router.callback_query(F.data == "edit_city")
async def start_edit_city(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Обработчик start_edit_city вызван для telegram_id={callback.from_user.id}")
    await callback.message.answer("Введите ID города и новое название (например, '1 Алматы'):")
    await state.set_state(AdminPanel.edit_city)
    await callback.answer()

@router.message(AdminPanel.edit_city)
async def process_edit_city(message: Message, state: FSMContext):
    logger.info(f"Обработчик process_edit_city вызван для telegram_id={message.from_user.id}")
    telegram_id = get_user_telegram_id(message)
    try:
        parts = message.text.strip().split(" ", 1)
        if len(parts) != 2:
            await message.answer("Пожалуйста, введите ID и новое название через пробел (например, '1 Алматы').")
            return
        city_id, new_name = parts[0], parts[1]
        city_id = int(city_id)
        # Предполагается, что API принимает PUT-запрос для изменения города
        await api_request("PUT", f"{API_URL}city/{city_id}", telegram_id, data={"name": new_name})
        await message.answer(f"Город с ID {city_id} изменён на '{new_name}'.", reply_markup=get_main_keyboard({"is_admin": True}))
    except ValueError:
        await message.answer("ID города должен быть числом.")
    except Exception as e:
        logger.error(f"Ошибка в process_edit_city: {e}")
        await message.answer(f"Ошибка изменения города: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()

@router.callback_query(F.data == "delete_city")
async def start_delete_city(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Обработчик start_delete_city вызван для telegram_id={callback.from_user.id}")
    await callback.message.answer("Введите ID города для удаления:")
    await state.set_state(AdminPanel.delete_city)
    await callback.answer()

@router.message(AdminPanel.delete_city)
async def process_delete_city(message: Message, state: FSMContext):
    logger.info(f"Обработчик process_delete_city вызван для telegram_id={message.from_user.id}")
    telegram_id = get_user_telegram_id(message)
    try:
        city_id = int(message.text)
        # Предполагается, что API принимает DELETE-запрос для удаления города
        await api_request("DELETE", f"{API_URL}city/{city_id}", telegram_id)
        await message.answer(f"Город с ID {city_id} удалён.", reply_markup=get_main_keyboard({"is_admin": True}))
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID (число).")
    except Exception as e:
        logger.error(f"Ошибка в process_delete_city: {e}")
        await message.answer(f"Ошибка удаления города: {e}", reply_markup=get_main_keyboard({"is_admin": True}))
    await state.clear()

@router.callback_query(F.data == "back")
async def back_to_main(callback: CallbackQuery):
    logger.info(f"Обработчик back_to_main вызван для telegram_id={callback.from_user.id}")
    telegram_id = callback.from_user.id
    try:
        user = await api_request("GET", f"{API_URL}user/me", telegram_id)
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": user["is_executor"], "is_customer": user["is_customer"]}
    except Exception as e:
        logger.error(f"Ошибка в back_to_main: {e}")
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": False}
    await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard(roles))
    await callback.answer()