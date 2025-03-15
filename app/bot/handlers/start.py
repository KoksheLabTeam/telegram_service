from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.bot.config import ADMIN_TELEGRAM_ID, API_URL
from app.bot.handlers.utils import api_request, get_user_telegram_id
import aiohttp
import logging

router = Router()
logger = logging.getLogger(__name__)

def get_main_keyboard(is_admin: bool = False, is_executor: bool = False, is_customer: bool = False):
    buttons = [
        [KeyboardButton(text="Профиль"), KeyboardButton(text="Создать заказ")],
        [KeyboardButton(text="Список заказов"), KeyboardButton(text="Сменить роль")]
    ]
    if is_executor:
        buttons.append([KeyboardButton(text="Создать предложение")])
    if is_customer:
        buttons.append([KeyboardButton(text="Посмотреть предложения")])
    if is_admin:
        buttons.append([KeyboardButton(text="Админ-панель")])
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        row_width=2
    )

async def api_request_no_auth(method: str, url: str):
    async with aiohttp.ClientSession() as session:
        if method == "GET":
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Ошибка {response.status}: {await response.text()}")
                return await response.json()

@router.message(Command("start"))
async def start_command(message: Message):
    is_admin = message.from_user.id == ADMIN_TELEGRAM_ID
    telegram_id = get_user_telegram_id(message)
    try:
        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
        is_executor = user["is_executor"]
        is_customer = user["is_customer"]
    except Exception as e:
        if "404" in str(e):
            try:
                cities = await api_request_no_auth("GET", f"{API_URL}city/")
                if not cities:
                    await message.answer("В системе нет городов. Обратитесь к администратору.")
                    return
                city_id = cities[0]["id"]
            except Exception as city_error:
                await message.answer(f"Ошибка с городами: {city_error}")
                return

            user_data = {
                "telegram_id": telegram_id,
                "name": message.from_user.full_name or "Unnamed",
                "username": message.from_user.username,
                "is_customer": True,
                "is_executor": False,
                "city_id": city_id
            }
            try:
                await api_request("POST", f"{API_URL}user/", telegram_id, data=user_data)
                is_executor = False
                is_customer = True
            except Exception as create_error:
                await message.answer(f"Ошибка создания профиля: {create_error}")
                return
        else:
            await message.answer(f"Ошибка при проверке профиля: {e}")
            return
    await message.answer("Добро пожаловать!", reply_markup=get_main_keyboard(is_admin, is_executor, is_customer))

@router.message(F.text == "Профиль")
async def show_profile(message: Message):
    telegram_id = get_user_telegram_id(message)
    try:
        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
        role = "Заказчик" if user["is_customer"] else "Исполнитель" if user["is_executor"] else "Не определена"
        city = await api_request("GET", f"{API_URL}city/{user['city_id']}", telegram_id)
        text = f"Имя: {user['name']}\nРоль: {role}\nГород: {city['name']}\nРейтинг: {user['rating']}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить имя", callback_data="update_name")],  # Исправлен callback_data
            [InlineKeyboardButton(text="Назад", callback_data="back")]
        ])
        await message.answer(text, reply_markup=keyboard)
    except Exception as e:
        await message.answer(f"Ошибка загрузки профиля: {e}", reply_markup=get_main_keyboard())

@router.message(F.text == "Список заказов")
async def show_orders(message: Message):  # Исправлено имя функции
    telegram_id = get_user_telegram_id(message)
    try:
        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
        is_executor = user["is_executor"]
        is_customer = user["is_customer"]
        is_admin = telegram_id == ADMIN_TELEGRAM_ID
        if is_executor:
            url = f"{API_URL}order/available"
            logger.info(f"Запрос для исполнителя: {url}")
            orders = await api_request("GET", url, telegram_id)
            title = "Доступные заказы:"
        else:
            url = f"{API_URL}order/"
            logger.info(f"Запрос для заказчика: {url}")
            orders = await api_request("GET", url, telegram_id)
            title = "Ваши заказы:"

        if not orders:
            await message.answer(f"{title.split(':')[0]} пока нет.", reply_markup=get_main_keyboard(is_admin, is_executor, is_customer))
            return

        response = f"{title}\n\n"
        for order in orders:
            status_map = {
                "pending": "Ожидает",
                "in_progress": "В процессе",
                "completed": "Завершён",
                "canceled": "Отменён"
            }
            status = status_map.get(order["status"], order["status"])
            due_date = order["due_date"].split("T")[0]
            response += (
                f"ID: {order['id']}\n"
                f"Название: {order['title']}\n"
                f"Статус: {status}\n"
                f"Желаемая цена: {order['desired_price']} тенге\n"
                f"Срок: {due_date}\n\n"
            )
        await message.answer(response.strip(), reply_markup=get_main_keyboard(is_admin, is_executor, is_customer))
    except Exception as e:
        logger.error(f"Ошибка в show_orders: {e}")
        await message.answer(f"Ошибка загрузки заказов: {e}", reply_markup=get_main_keyboard())

@router.callback_query(F.data == "update_name")
async def update_name(callback: CallbackQuery):
    await callback.message.answer("Функция изменения имени пока не реализована.")
    await callback.answer()

@router.callback_query(F.data == "back")
async def back_to_main(callback: CallbackQuery):
    is_admin = callback.from_user.id == ADMIN_TELEGRAM_ID
    telegram_id = callback.from_user.id
    try:
        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
        is_executor = user["is_executor"]
        is_customer = user["is_customer"]
    except Exception:
        is_executor = False
        is_customer = False
    await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard(is_admin, is_executor, is_customer))
    await callback.answer()