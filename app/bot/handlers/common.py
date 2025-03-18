import aiohttp
from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from app.bot.config import ADMIN_TELEGRAM_ID, API_URL
import logging

logger = logging.getLogger(__name__)

# Общий роутер для утилит
common_router = Router()

# Функция для выполнения API-запросов
async def api_request(method: str, url: str, telegram_id: int, data: dict = None):
    headers = {"x-telegram-id": str(telegram_id)}
    logger.info(f"Выполняется запрос: {method} {url} с headers={headers}")
    async with aiohttp.ClientSession() as session:
        try:
            if method == "GET":
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ошибка {response.status}: {error_text}")
                    return await response.json()
            elif method == "POST":
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status not in (200, 201):
                        raise Exception(f"Ошибка {response.status}: {await response.text()}")
                    return await response.json()
            elif method == "PATCH":
                async with session.patch(url, headers=headers, json=data) as response:
                    if response.status != 200:
                        raise Exception(f"Ошибка {response.status}: {await response.text()}")
                    text = await response.text()
                    if not text:  # Проверяем, есть ли тело ответа
                        raise Exception("Сервер вернул пустой ответ")
                    return await response.json()
            elif method == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    if response.status != 204:
                        raise Exception(f"Ошибка {response.status}: {await response.text()}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса {method} {url}: {e}")
            raise

# Функция для выполнения API-запросов без авторизации
async def api_request_no_auth(method: str, url: str):
    async with aiohttp.ClientSession() as session:
        if method == "GET":
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Ошибка {response.status}: {await response.text()}")
                return await response.json()

# Получение Telegram ID пользователя
def get_user_telegram_id(message: Message) -> int:
    return message.from_user.id

# Основная клавиатура
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(roles: dict = None) -> ReplyKeyboardMarkup:
    roles = roles or {}
    buttons = [
        [KeyboardButton(text="Профиль"), KeyboardButton(text="Список заказов")],
        [KeyboardButton(text="Сменить роль")]
    ]
    # "Создать заказ" только для заказчиков
    if roles.get("is_customer"):
        buttons[0].insert(1, KeyboardButton(text="Создать заказ"))
    # "Создать предложение" только для исполнителей
    if roles.get("is_executor"):
        buttons.append([KeyboardButton(text="Создать предложение")])
    if roles.get("is_customer"):
        buttons.append([KeyboardButton(text="Посмотреть предложения")])
    if roles.get("is_admin"):
        buttons.append([KeyboardButton(text="Админ панель")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Функция для получения роли пользователя
async def get_user_roles(telegram_id: int) -> dict:
    try:
        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
        return {
            "is_admin": telegram_id == ADMIN_TELEGRAM_ID,
            "is_executor": user["is_executor"],
            "is_customer": user["is_customer"]
        }
    except Exception as e:
        logger.error(f"Ошибка получения ролей пользователя: {e}")
        return {"is_admin": False, "is_executor": False, "is_customer": False}